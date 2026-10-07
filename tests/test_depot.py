import json
from defuse.depot.game import Depot, load_bank, CONTENT_BINS, CONTINENT_BINS, SWITCH_AT, PER_ROUND, RECENT, BANK
from defuse.depot.runner import run_game, keyword_choice
from defuse.depot.render import TEXT_PAIRS, contrast, BIN_COLOR, CARD
from defuse.depot.report import report


def test_item_bank_has_one_clear_bin_and_a_reason_for_every_item():
    contents, messy, cities = load_bank()
    assert len(contents) >= 160 and len(messy) >= 128
    for item in contents:
        assert item['bin'] in CONTENT_BINS and item['why'].strip() and item['label'].strip()
    for item in messy:
        assert item['bin'] in CONTENT_BINS and item['meaning'].strip()
    labels = [i['label'].lower() for i in contents + messy]
    assert len(labels) == len(set(labels))
    places = [c for v in cities.values() for c in v]
    assert set(cities) == set(CONTINENT_BINS) and len(places) == len(set(places))


def test_keyword_baseline_does_not_know_the_items():
    vocab = json.loads((BANK / 'keyword_baseline.json').read_text())
    contents, messy, _ = load_bank()
    words = {w for k in CONTENT_BINS if k != 'other' for w in vocab[k]}
    assert not words & {i['label'].lower() for i in contents + messy}
    assert not any(i['id'] in json.dumps(vocab) for i in contents + messy)


def test_answer_key_is_consistent_over_200_seeds():
    for seed in range(200):
        d = Depot(seed)
        assert len(d.packages) == 5 * PER_ROUND
        prompts = [d.prompt(p) for p in d.packages]
        assert len(prompts) == len(set(prompts))
        labels = [p['label'] for p in d.packages if p['rule'] != 'memory']
        assert len(labels) == len(set(labels))
        for p in d.packages:
            assert p['bin'] in {o['id'] for o in d.options(p)}
            assert p['bin'] not in d.prompt(p).split('Package')[-1].lower() or p['rule'] == 'memory'
        switch = [p for p in d.packages if p['round'] == 'switch']
        assert all(p['rule'] == 'contents' for p in switch[:SWITCH_AT]) and all(p['rule'] == 'continent' for p in switch[SWITCH_AT:])
        for p in switch[SWITCH_AT:]:
            assert d.options(p) == [{'id': k, 'description': v} for k, v in CONTINENT_BINS.items()]
            assert 'New rule' in d.prompt(p)
        for p in d.packages:
            if p['rule'] == 'memory':
                recent = d.recent(p)
                refs = [q for q in recent if q['origin'] == p['ref_city']]
                assert len(recent) <= RECENT and len(refs) == 1 and refs[0]['bin'] == p['bin']
        listed = [p for p in d.packages if p['round'] == 'list']
        assert sum(p['rule'] == 'manifest' for p in listed) == 8
        assert all(p['bin'] == d.manifest[p['destination']] for p in listed if p['rule'] == 'manifest')


def test_keyword_baseline_follows_rules_it_can_parse():
    d = Depot(5)
    for p in d.packages:
        if p['rule'] in ('manifest', 'memory'):
            assert keyword_choice(d, p) == p['bin']


def test_offline_baselines_and_stubbed_decisions(tmp_path, stub):
    folder, r = run_game(4, 'oracle', 'realtime', output=tmp_path, video=False, dwell=0, intro=0)
    assert r['correct'] == r['packages'] == 100 and r['end_reason'] == 'complete'
    assert (folder / 'captions.srt').read_text().count('-->') == 200
    assert len((folder / 'transcript.tsv').read_text().splitlines()) == 101
    folder, r = run_game(4, 'decisions', 'paused', output=tmp_path, endpoint=stub['url'], video=False, dwell=0, intro=0)
    assert r['requests'] == 100 and r['cost_usd'] == 0 and r['timeout'] == 10.0
    body = stub['requests'][0]
    assert body['input'][0]['content'][0]['text'].startswith('Sorting depot, round 1 of 5') and 'Hazardous, Cold, Fragile' in body['input'][0]['content'][0]['text']
    assert body['questions'][0]['instructions'] == 'Which bin does this package go into?'
    assert len(body['questions'][0]['choices']) == 4
    stub['delay'] = 0.3
    folder, r = run_game(4, 'decisions', 'realtime', output=tmp_path, endpoint=stub['url'], timeout=0.1, video=False, dwell=0, intro=0, rounds=['know'])
    assert r['no_answer'] == 20 and r['correct'] == 0
    payload = report(tmp_path)
    assert {(g['controller'], g['timing']) for g in payload['groups']} >= {('oracle', 'realtime'), ('decisions', 'paused')}


def test_short_video_renders_with_captions(tmp_path):
    folder, r = run_game(6, 'keyword', 'paused', output=tmp_path, video=True, dwell=0.05, intro=0.2, rounds=['know'])
    assert r['video_status'] == 'complete' and (folder / 'gameplay.mp4').stat().st_size > 0
    assert (folder / 'captions.srt').read_text().count('-->') == 40


def test_palette_is_readable():
    assert all(contrast(fg, bg) >= 4.5 for fg, bg in TEXT_PAIRS)
    assert all(contrast(c, CARD) >= 3.0 for c in BIN_COLOR.values())   # icons and outlines: non-text contrast


def test_frozen_baselines_read_only_the_prompt_and_keep_the_manifest_in_its_round():
    from defuse.depot import baselines
    d = Depot(103)
    tea = next(p for p in d.packages if p['label'] == 'ceramic tea set')   # switch round, destination on the manifest
    assert tea['round'] == 'switch' and baselines.keyword(d.prompt(tea)) == 'fragile'
    for p in d.packages:
        prompt = d.prompt(p)
        assert p['bin'] not in prompt.splitlines()[-1].split('"')[1:2] or p['rule'] == 'memory'
    scores = {name: sum(f(Depot(s).prompt(p)) == p['bin'] for s in range(101, 106) for p in Depot(s).packages)
              for name, f in baselines.CONTROLLERS.items()}
    assert scores == {'keyword': 350, 'dictionary': 493}   # the review's published numbers, plus the manifest fix


def test_report_drops_repeated_seeds_and_captions_wait_for_the_answer(tmp_path):
    from defuse.depot.render import caption_cues, captions_for
    folder, _ = run_game(101, 'keyword', 'realtime', output=tmp_path, video=False, dwell=0, intro=0, rounds=['know'])
    run_game(101, 'keyword', 'realtime', output=tmp_path, video=False, dwell=0, intro=0, rounds=['know'])
    payload = report(tmp_path)
    group = next(g for g in payload['groups'] if g['controller'] == 'keyword')
    assert group['runs'] == 1 and group['total'] == 20 and len(payload['duplicates']) == 1
    rows = [json.loads(l) for l in (folder / 'actions.jsonl').read_text().splitlines()]
    cues = caption_cues(folder)
    outcome = [c for c in cues if ' chose ' in c[2]]
    assert all(abs(c[0] - r['decision_at']) < 1e-9 for c, r in zip(outcome, rows))
    part = captions_for(folder, 0.0, rows[5]['request_at'])
    assert part.count('-->') == 10 and part.startswith('1\n00:00:00')
