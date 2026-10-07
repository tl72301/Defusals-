"""Summaries from recorded evidence; duplicate seeds are explicitly excluded per condition."""
from collections import defaultdict, Counter
import csv
import json
from pathlib import Path
import numpy as np
from defuse.render import read_jsonl

def load_runs(root):
    runs=[]
    for p in sorted(Path(root).rglob('results.json')):
        r=json.loads(p.read_text()); m=json.loads((p.parent/'manifest.json').read_text()); a=read_jsonl(p.parent/'actions.jsonl')
        if r['actions']!=len(a) or r['correct_actions']!=sum(x['correct'] for x in a): raise ValueError('action/result mismatch: '+str(p))
        if r['run_id']!=m['run_id'] or r['seed']!=m['seed']: raise ValueError('manifest/result mismatch: '+str(p))
        runs.append((p.parent,r,m,a))
    return runs

def rank(run):
    _,r,_,_=run
    return (r['defused'],r['modules_solved'],-r['strikes'],r['time_left'])

def report(root,output=None):
    root=Path(root); output=Path(output or root/'report'); output.mkdir(parents=True,exist_ok=True)
    runs=load_runs(root)
    if not runs: raise ValueError('No completed attempts found')
    groups=defaultdict(list); seen=set(); duplicates=[]
    for run in runs:
        p,r,m,a=run
        condition=(r['controller'],r['timing'],r['difficulty'],r['stub'],m['limits']['seconds'],m['limits']['step_seconds'],m['limits']['timeout'],m['limits']['max_requests'],m['code_revision'].get('source_sha256'),m.get('scenario','bomb'),m.get('keystone_depth') or 0)
        key=condition+(r['seed'],)
        if key in seen: duplicates.append(str(p)); continue
        seen.add(key); groups[condition].append(run)
    summaries=[]
    for condition,items in sorted(groups.items()):
        actions=[a for _,_,_,aa in items for a in aa]; results=[r for _,r,_,_ in items]
        latency=[a['answer']['latency'] for a in actions]; bymodule=defaultdict(lambda:[0,0]); positions=Counter(); opportunities=Counter()
        for a in actions:
            bymodule[a['module_type']][0]+=int(a['correct']); bymodule[a['module_type']][1]+=1
            if a['answer']['choice']: positions[a['answer']['choice']]+=1
            for o in a['options']: opportunities[o['value']]+=1
        mazes=[]; depths=defaultdict(lambda:[0,0])
        for path,result,manifest,recorded in items:
            for module in result['final_state']['modules']:
                if module['kind']!='labyrinth': continue
                moves=[a for a in recorded if a['module_id']==module['id'] and 'move_legal' in a]
                legal_count=sum(a['move_legal'] for a in moves); shortest_count=sum(a['on_shortest_path'] for a in moves)
                mazes.append({'run':str(path),'seed':result['seed'],'module_id':module['id'],'solved':module['solved'],
                              'strikes':len(moves)-legal_count,'moves_taken':len(moves),'legal_moves':legal_count,
                              'shortest_moves':shortest_count,'optimal_moves':module['optimal_moves'],
                              'legal_move_rate':legal_count/len(moves) if moves else None,
                              'shortest_path_rate':shortest_count/len(moves) if moves else None,
                              'excess_moves_if_solved':len(moves)-module['optimal_moves'] if module['solved'] else None})
            for action in recorded:
                if action['module_type']=='keystone':
                    depth=action['state_shown']['state']['depth']; depths[depth][0]+=action['correct']; depths[depth][1]+=1
        maze_moves=sum(m['moves_taken'] for m in mazes)
        summary={'controller':condition[0],'timing':condition[1],'difficulty':condition[2],'stub':condition[3],
                 'scenario':condition[9],'keystone_depth':condition[10] or None,
                 'limits':items[0][2]['limits'],'source_sha256':condition[8],
                 'attempts':len(items),'unique_seeds':len({r['seed'] for r in results}),'bombs_defused':sum(r['defused'] for r in results),
                 'mean_modules_solved':float(np.mean([r['modules_solved'] for r in results])),
                 'mean_strikes':float(np.mean([r['strikes'] for r in results])),'mean_time_left':float(np.mean([r['time_left'] for r in results])),
                 'latency_p50':float(np.percentile(latency,50)) if latency else None,'latency_p95':float(np.percentile(latency,95)) if latency else None,
                 'input_tokens':sum(r['input_tokens'] for r in results),'cost_usd':sum(r['cost_usd'] for r in results),
                 'billing_unknown_requests':sum(r['billing_unknown_requests'] for r in results),'decision_accuracy_by_module':{k:{'correct':v[0],'total':v[1],'accuracy':v[0]/v[1]} for k,v in sorted(bymodule.items())},
                 'position_counts':dict(positions),'position_opportunities':dict(opportunities),
                 'first_option_fraction':positions['A']/sum(positions.values()) if positions else None,
                 'uniform_expected_first_fraction':float(np.mean([1/len(a['options']) for a in actions])) if actions else None,
                 'labyrinth':{'per_maze':mazes,'moves_taken':maze_moves,'strikes':sum(m['strikes'] for m in mazes),
                              'legal_move_rate':sum(m['legal_moves'] for m in mazes)/maze_moves if maze_moves else None,
                              'shortest_path_rate':sum(m['shortest_moves'] for m in mazes)/maze_moves if maze_moves else None},
                 'keystone_accuracy_by_depth':{str(d):{'correct':v[0],'total':v[1],'accuracy':v[0]/v[1],'random_chance':.25} for d,v in sorted(depths.items())},
                 'best':str(max(items,key=rank)[0]),'worst':str(min(items,key=rank)[0])}
        summaries.append(summary)
    best=str(max(runs,key=rank)[0]); worst=str(min(runs,key=rank)[0])
    payload={'groups':summaries,'duplicate_attempts_excluded':duplicates,'best':best,'worst':worst,
             'notes':['Conditions include difficulty, limits, code hash and stub status. Matched seeds across controllers are paired observations, not independent samples.',
                      'Realtime is the headline condition. Paused is judgment without time pressure. Stub tokens are synthetic and cost $0.',
                      'Costs exclude unreported billing for failed/timed-out live requests; their conservative reservations remain in the private ledger.']}
    (output/'report.json').write_text(json.dumps(payload,indent=2))
    fields=['controller','timing','difficulty','scenario','keystone_depth','stub','attempts','bombs_defused','mean_modules_solved','mean_strikes','mean_time_left','latency_p50','latency_p95','input_tokens','cost_usd','first_option_fraction']
    with open(output/'summary.csv','w') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); writer.writeheader(); writer.writerows(summaries)
    lines=['# Defuse × Decisions — recorded results','',*payload['notes'],'',
           '| Controller | Timing | Difficulty | n seeds | Defused | Modules avg | Strikes avg | Time left avg | p50 / p95 ms | Tokens | USD | Chose A |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        lat='—' if s['latency_p50'] is None else f'{s["latency_p50"]*1000:.1f} / {s["latency_p95"]*1000:.1f}'
        pos='—' if s['first_option_fraction'] is None else f'{s["first_option_fraction"]:.1%}'
        lines.append(f'| {s["controller"]}{" (STUB)" if s["stub"] else ""} | {s["timing"]} | {s["difficulty"]} | {s["attempts"]} | {s["bombs_defused"]} | {s["mean_modules_solved"]:.2f} | {s["mean_strikes"]:.2f} | {s["mean_time_left"]:.2f} | {lat} | {s["input_tokens"]} | {s["cost_usd"]:.7f} | {pos} |')
    lines+=['','## Accuracy by module','', '| Controller / timing / difficulty | Module | Correct / decisions | Accuracy |','|---|---|---:|---:|']
    for s in summaries:
        for k,v in s['decision_accuracy_by_module'].items(): lines.append(f'| {s["controller"]} / {s["timing"]} / {s["difficulty"]} | {k} | {v["correct"]}/{v["total"]} | {v["accuracy"]:.1%} |')
    lines+=['','## Labyrinth','', 'Shortest-path rate uses all attempted moves as its denominator. Legal detours do not strike. Incomplete mazes have no excess-move estimate.','',
            '| Controller / timing | Seed | Strikes | Legal move rate | Shortest-path rate | Moves / optimal | Solved |','|---|---:|---:|---:|---:|---:|---|']
    for s in summaries:
        for maze in s['labyrinth']['per_maze']:
            legal_rate='—' if maze['legal_move_rate'] is None else f'{maze["legal_move_rate"]:.1%}'
            shortest_rate='—' if maze['shortest_path_rate'] is None else f'{maze["shortest_path_rate"]:.1%}'
            lines.append(f'| {s["controller"]} / {s["timing"]} | {maze["seed"]} | {maze["strikes"]} | {legal_rate} | {shortest_rate} | {maze["moves_taken"]}/{maze["optimal_moves"]} | {maze["solved"]} |')
    lines+=['','## Keystone accuracy by depth','', 'Sweep conditions use one choice per independent seed/depth; ordinary-module figures include retries. A final key choice does not reveal the model’s intermediate reasoning. Oracle traces support audit but cannot locate a model’s first mistaken step.','',
            '| Controller / timing / condition | Depth | Correct / choices | Accuracy | Random chance |','|---|---:|---:|---:|---:|']
    for s in summaries:
        for depth,values in s['keystone_accuracy_by_depth'].items():
            lines.append(f'| {s["controller"]} / {s["timing"]} / {s["scenario"]} | {depth} | {values["correct"]}/{values["total"]} | {values["accuracy"]:.1%} | 25% |')
    lines+=['','## Position bias','', 'Counts and opportunity-normalized statistics are in report.json. The random expectation adjusts for the number of legal options.','']
    for s in summaries: lines.append(f'- {s["controller"]} / {s["timing"]} / {s["difficulty"]}: {s["position_counts"]}; uniform expected A = {s["uniform_expected_first_fraction"]}.')
    lines+=['',f'Best attempt: `{best}`',f'Worst attempt: `{worst}`','',f'Duplicate attempts excluded: {len(duplicates)}. Repeated seeds within a condition are never counted as independent samples.','']
    (output/'summary.md').write_text('\n'.join(lines))
    return payload
