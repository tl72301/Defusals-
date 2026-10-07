import argparse
from defuse.gauntlet.runner import run_ladder, run_throughput, PLAYERS


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m defuse.gauntlet')
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run'); r.add_argument('--ladder', required=True, choices='ABCD'); r.add_argument('--player', required=True, choices=PLAYERS)
    r.add_argument('--rungs', type=int, nargs='*'); r.add_argument('--output', default='data/gauntlet'); r.add_argument('--endpoint')
    t = sub.add_parser('throughput'); t.add_argument('--player', required=True, choices=PLAYERS); t.add_argument('--sizes', type=int, nargs='*')
    t.add_argument('--output', default='data/gauntlet'); t.add_argument('--endpoint')
    sub.add_parser('report').add_argument('--output', default='data/gauntlet')
    a = p.parse_args(argv)
    if a.cmd == 'run':
        rows = run_ladder(a.ladder, a.player, a.output, a.endpoint, a.rungs)
        print(f'{a.player} ladder {a.ladder}: {sum(r["correct"] for r in rows)}/{len(rows)} correct')
    elif a.cmd == 'throughput':
        rows = [r for r in run_throughput(a.player, a.output, a.endpoint, a.sizes) if not r.get('summary')]
        print(f'{a.player} throughput: {sum(r["correct"] for r in rows)}/{len(rows)} correct')
    else:
        from defuse.gauntlet.report import report
        report(a.output)


if __name__ == '__main__':
    main()
