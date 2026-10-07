#!/usr/bin/env python3
"""Validate completed experiment artifacts; no network and no new game attempts."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=Path, required=True)
    p.add_argument('--expected-runs', type=int)
    args = p.parse_args()
    probe = shutil.which('ffprobe')
    if not probe:
        p.error('ffprobe is required for this optional independent media audit')
    results = sorted(args.runs.rglob('results.json'))
    if args.expected_runs is not None:
        assert len(results) == args.expected_runs, (len(results), args.expected_runs)
    checks = []
    for path in results:
        folder = path.parent
        result = json.loads(path.read_text())
        manifest = json.loads((folder / 'manifest.json').read_text())
        actions = [json.loads(line) for line in (folder / 'actions.jsonl').read_text().splitlines()]
        usage = [json.loads(line) for line in (folder / 'api-usage.jsonl').read_text().splitlines()]
        assert result['run_id'] == manifest['run_id']
        assert len(actions) == result['actions']
        assert sum(a['correct'] for a in actions) == result['correct_actions']
        assert len(usage) == result['requests']
        assert sum(u['input_tokens'] or 0 for u in usage) == result['input_tokens']
        assert abs(sum(u['cost_usd'] for u in usage) - result['cost_usd']) < 1e-10
        assert sum(u['billing_unknown'] for u in usage) == result['billing_unknown_requests']
        assert result['video_status'] == 'complete'
        metadata = json.loads(subprocess.check_output([
            probe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(folder / 'gameplay.mp4')
        ]))
        stream = metadata['streams'][0]
        assert (stream['width'], stream['height'], stream['codec_name'], stream['r_frame_rate']) == (1280, 720, 'h264', '30/1')
        assert int(stream['nb_frames']) == result['video']['frames']
        error = abs(float(metadata['format']['duration']) - result['wall_duration'])
        assert error <= 1 / 30 + .001, (folder, error)
        checks.append({'run_id': result['run_id'], 'duration_error_seconds': error, 'frames': int(stream['nb_frames'])})
    reviews = sorted((args.runs / 'clips').glob('*.mp4'))
    for clip in reviews:
        assert 0 < clip.stat().st_size < 25_000_000
    payload = {'runs_verified': len(checks), 'checks': checks, 'review_files_verified': len(reviews),
               'largest_review_bytes': max((p.stat().st_size for p in reviews), default=0),
               'reported_cost_usd': sum(json.loads(p.read_text())['cost_usd'] for p in results)}
    (args.runs / 'artifact-validation.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: v for k, v in payload.items() if k != 'checks'}, indent=2))


if __name__ == '__main__':
    main()
