"""Sorting Depot command line: python -m defuse.depot run|batch|report|clips"""
import argparse
import sys
from pathlib import Path
from defuse.budget import Budget, DEFAULT_DIR
from defuse.decisions import API_URL
from defuse.depot.runner import CONTROLLERS, TIMINGS, run_game, summary_line


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m defuse.depot', description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('run', 'batch'):
        a = sub.add_parser(name)
        if name == 'run':
            a.add_argument('--seed', type=int, required=True)
            a.add_argument('--controller', choices=CONTROLLERS, default='oracle')
            a.add_argument('--timing', choices=TIMINGS, default='realtime')
        else:
            a.add_argument('--seeds', type=int, nargs='+', required=True)
            a.add_argument('--controllers', choices=CONTROLLERS, nargs='+', default=['oracle', 'keyword', 'dictionary', 'random', 'first_option'])
            a.add_argument('--timings', choices=TIMINGS, nargs='+', default=['realtime'])
        a.add_argument('--output', type=Path, default=Path('data/depot'))
        a.add_argument('--endpoint', default=API_URL)
        a.add_argument('--timeout', type=float, default=None, help='Request deadline; default 1.5 s realtime, 10 s paused')
        a.add_argument('--bank', choices=['v1', 'v2'], default='v1', help='v1: development bank; v2: separately authored test bank')
        a.add_argument('--budget-dir', type=Path, default=DEFAULT_DIR)
        a.add_argument('--no-video', action='store_true')
        a.add_argument('--dwell', type=float, default=0.6, help='Pause after each package (paces the video)')
        a.add_argument('--intro', type=float, default=2.0, help='Round introduction card, seconds')
    for name in ('report', 'clips'):
        a = sub.add_parser(name); a.add_argument('--runs', type=Path, default=Path('data/depot')); a.add_argument('--output', type=Path)
    args = p.parse_args(argv)
    if args.command == 'report':
        from defuse.depot.report import report
        r = report(args.runs, args.output); print(f'Report written for {len(r["groups"])} conditions'); return 0
    if args.command == 'clips':
        from defuse.depot.report import clips
        print(f'{len(clips(args.runs, args.output))} review copies'); return 0
    common = dict(output=args.output, endpoint=args.endpoint, timeout=args.timeout, budget=Budget(args.budget_dir),
                  video=not args.no_video, dwell=args.dwell, intro=args.intro, bank=args.bank)
    if args.command == 'run':
        folder, r = run_game(args.seed, args.controller, args.timing, **common)
        print(summary_line(folder, r)); return 0 if not r['errors'] else 2
    if len(set(args.seeds)) != len(args.seeds):
        raise SystemExit('Repeated seeds are not allowed in one batch')
    failed = False
    for seed in args.seeds:
        for controller in args.controllers:
            for timing in args.timings:
                folder, r = run_game(seed, controller, timing, batch=True, **common)
                print(summary_line(folder, r), flush=True)
                failed = failed or bool(r['errors'])
                if r['end_reason'] == 'budget_or_configuration_blocked':
                    return 2
    return 2 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
