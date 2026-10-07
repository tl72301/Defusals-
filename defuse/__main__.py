"""Command-line entry point. Offline commands never touch the Decisions endpoint."""
if __name__ == '__main__':
    from defuse._environment import bootstrap
    bootstrap('defuse')

import argparse
import json
from pathlib import Path
import sys
from defuse.budget import Budget, DEFAULT_DIR
from defuse.decisions import API_URL
from defuse.runner import run_attempt, summary_line, CONTROLLERS, TIMINGS


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ('budget','doctor'):
        if argv[0]=='budget': from defuse.budget import main as entry
        else: from defuse.doctor import main as entry
        return entry(argv[1:])
    p=argparse.ArgumentParser(description='Defuse × Decisions — original timed reasoning benchmark')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['attempt','batch','smoke','sweep']:
        a=sub.add_parser(name,aliases=['keystone-sweep'] if name=='sweep' else [])
        a.add_argument('--difficulty',choices=['easy','medium','hard'],default='medium'); a.add_argument('--seconds',type=float,default=180)
        a.add_argument('--output',type=Path,default=Path('data/runs')); a.add_argument('--endpoint',default=API_URL); a.add_argument('--timeout',type=float,default=.6)
        a.add_argument('--budget-dir',type=Path,default=DEFAULT_DIR); a.add_argument('--no-video',action='store_true'); a.add_argument('--step-seconds',type=float,default=.2)
        a.add_argument('--max-requests',type=int,default=300)
        if name in ('batch','sweep'):
            if name=='batch': a.add_argument('--seeds',type=int,nargs='+',required=True)
            else:
                a.add_argument('--seeds',type=int,default=20,help='Number of unique seeds per depth')
                a.add_argument('--seed-start',type=int,default=0)
                a.add_argument('--depths',type=int,nargs='+',default=[1,2,3,4,5])
            a.add_argument('--controllers',choices=CONTROLLERS,nargs='+',default=['solver','random','first_option'])
            a.add_argument('--timings',choices=TIMINGS,nargs='+',default=['realtime'])
        else:
            a.add_argument('--seed',type=int,required=True); a.add_argument('--timing',choices=TIMINGS,default='realtime')
            if name=='attempt': a.add_argument('--controller',choices=CONTROLLERS,default='solver')
            else: a.add_argument('--requests',type=int,default=30)
    for name in ['report','clips']:
        a=sub.add_parser(name); a.add_argument('--runs',type=Path,default=Path('data/runs')); a.add_argument('--output',type=Path)
    a=sub.add_parser('manual'); a.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    try:
        if args.command=='manual':
            from defuse.manual import markdown
            if args.output: args.output.write_text(markdown())
            else: print(markdown())
            return 0
        if args.command=='report':
            from defuse.reports import report
            r=report(args.runs,args.output); print(f'Report written: {args.output or args.runs/"report"}; {len(r["groups"])} conditions'); return 0
        if args.command=='clips':
            from defuse.clips import clips
            r=clips(args.runs,args.output); print(f'{len(r["clips"])} review copies; highlight: {r["highlight"]}'); return 0
        common=dict(difficulty=args.difficulty,seconds=args.seconds,output=args.output,endpoint=args.endpoint,timeout=args.timeout,
                    budget=Budget(args.budget_dir),video=not args.no_video,step_seconds=args.step_seconds,max_requests=args.max_requests)
        if args.command in ('sweep','keystone-sweep'):
            if args.seeds<1 or not args.depths or any(d not in range(1,6) for d in args.depths) or len(set(args.depths))!=len(args.depths):
                raise ValueError('Sweep needs positive N seeds and unique depths 1..5')
            if len(set(args.controllers))!=len(args.controllers) or len(set(args.timings))!=len(args.timings): raise ValueError('Duplicate conditions are not allowed')
            common['max_requests']=1
            failures=False
            for depth in args.depths:
                for offset in range(args.seeds):
                    seed=args.seed_start+(depth-1)*args.seeds+offset
                    for controller in args.controllers:
                        for timing in args.timings:
                            folder,r=run_attempt(seed,controller,timing,batch=True,keystone_depth=depth,**common)
                            print(f'depth={depth} '+summary_line(folder,r),flush=True)
                            failures=failures or bool(r['errors'])
                            if r['end_reason']=='budget_or_configuration_blocked': return 2
            from defuse.reports import report
            report(args.output)
            return 2 if failures else 0
        if args.command=='batch':
            if len(set(args.seeds))!=len(args.seeds): raise ValueError('Repeated seeds are not independent samples; supply unique seeds')
            if len(set(args.controllers))!=len(args.controllers) or len(set(args.timings))!=len(args.timings): raise ValueError('Duplicate conditions are not allowed')
            failures=False
            for seed in args.seeds:
                for controller in args.controllers:
                    for timing in args.timings:
                        folder,r=run_attempt(seed,controller,timing,batch=True,**common); print(summary_line(folder,r),flush=True)
                        failures=failures or bool(r['errors'])
                        if r['end_reason']=='budget_or_configuration_blocked': return 2
            return 2 if failures else 0
        if args.command=='smoke':
            if not 1<=args.requests<=30: raise ValueError('Smoke requests must be 1..30')
            common['max_requests']=args.requests
            folder,r=run_attempt(args.seed,'decisions',args.timing,category='smoke',**common)
        else: folder,r=run_attempt(args.seed,args.controller,args.timing,**common)
        print(summary_line(folder,r),flush=True)
        # A lost bomb is a valid completed experiment. Operational/API failures are nonzero.
        return 2 if r['errors'] or r['end_reason']=='budget_or_configuration_blocked' else 0
    except (ValueError,OSError,RuntimeError) as e:
        print(f'ERROR: {e}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
