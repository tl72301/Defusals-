"""python -m defuse.allergy run|build"""
import argparse
import json
from defuse.allergy import runner, bank


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m defuse.allergy')
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--split', choices=list(bank.SPLITS), required=True)
    r.add_argument('--systems', nargs='+', choices=runner.SYSTEMS, default=runner.SYSTEMS)
    r.add_argument('--root', default='data/allergy')
    r.add_argument('--limit', type=int, help='first N scenarios only (smoke tests)')
    r.add_argument('--endpoint')
    sub.add_parser('build')
    a = p.parse_args(argv)
    if a.cmd == 'build':
        bank.build()
    else:
        for s, v in runner.run(a.split, a.systems, a.root, a.endpoint, limit=a.limit).items():
            print(s, json.dumps(v))


if __name__ == '__main__':
    main()
