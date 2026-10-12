"""python -m defuse.launch run|tune|report|batching"""
import argparse
import json
from defuse.launch import runner, report, rules
from defuse.launch.runner import SYSTEMS, PARAMS_FILE

THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
FLIPS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]


def tune(root='data/launch', endpoint=None):
    """Development scenarios only. Order: fewest false clears, then unjustified holds, then clarifications."""
    from defuse.launch import bank
    scenarios = bank.load('dev') + bank.load('hard_dev')        # both development sets (§8, change 6)
    ex = runner.make_extractors(__import__('pathlib').Path(root), endpoint)
    chosen, grid = {}, {}
    for system, name, values in (('decisions-threshold', 'threshold', THRESHOLDS), ('decisions-sensitive', 'flip', FLIPS)):
        rows = []
        for v in values:
            s = runner.score([runner.run_scenario(sc, system, ex, {name: v}) for sc in scenarios])
            rows.append({name: v, **s})
        best = min(rows, key=lambda r: (r['false_clears'], r['unjustified_holds'], r['clarifications']))
        chosen[system] = {name: best[name]}
        grid[system] = rows
    PARAMS_FILE.write_text(json.dumps({**chosen, 'grid_on_dev': grid}, indent=1))
    return chosen, grid


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m defuse.launch')
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run'); r.add_argument('--split', choices=['dev', 'test', 'hard_dev', 'hard_test'], required=True)
    r.add_argument('--systems', nargs='+', choices=SYSTEMS, default=SYSTEMS); r.add_argument('--root', default='data/launch')
    r.add_argument('--endpoint')
    t = sub.add_parser('tune'); t.add_argument('--root', default='data/launch'); t.add_argument('--endpoint')
    rp = sub.add_parser('report'); rp.add_argument('--split', default='test'); rp.add_argument('--root', default='data/launch')
    b = sub.add_parser('batching'); b.add_argument('--split', default='test'); b.add_argument('--root', default='data/launch')
    a = p.parse_args(argv)
    if a.cmd == 'run':
        for s, v in runner.run(a.split, a.systems, a.root, a.endpoint).items():
            print(s, json.dumps(v))
    elif a.cmd == 'tune':
        chosen, _ = tune(a.root, a.endpoint)
        print(json.dumps(chosen))
    elif a.cmd == 'report':
        report.report(a.split, a.root)
    else:
        print(json.dumps(report.batching(a.split, a.root), indent=1))


if __name__ == '__main__':
    main()
