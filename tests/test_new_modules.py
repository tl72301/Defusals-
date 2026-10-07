from collections import deque
from copy import deepcopy
import json
import random
import pytest
from defuse.engine import Bomb
from defuse.modules import labyrinth, keystone
from defuse.__main__ import main
from defuse.runner import run_attempt


def test_nine_unique_marker_pairs_and_connected_original_layouts():
    pairs={frozenset(layout['markers']) for layout in labyrinth.LAYOUTS}
    assert len(pairs)==9
    geometries={layout['passages'] for layout in labyrinth.LAYOUTS}
    assert len(geometries)==9
    for layout in labyrinth.LAYOUTS:
        assert len(set(layout['markers']))==2
        assert len(layout['passages'])==35
        assert len(labyrinth.distances(layout,(6,6)))==36
        for start in [(r,c) for r in range(1,7) for c in range(1,7) if (r,c)!=(6,6)]:
            state={'markers':layout['markers'],'cell':list(start),'exit':[6,6]}
            optimal=labyrinth.distances(layout,(6,6))[start]
            for _ in range(optimal):
                action=labyrinth.shortest_action(state)
                assert labyrinth.legal(layout,state['cell'],action)
                state['cell']=list(labyrinth.destination(state['cell'],action))
            assert state['cell']==[6,6]


def test_1000_seeds_labyrinth_and_keystone_at_every_depth():
    seen=set()
    for seed in range(1000):
        bomb=Bomb(seed,'hard'); maze=bomb.current(); seen.add(labyrinth.layout_for(maze['state']['markers'])['id'])
        optimal=maze['optimal_moves']; moves=0
        while not maze['solved']:
            result=bomb.apply(bomb.answer()[0]); moves+=1
            assert result['move_legal'] and result['on_shortest_path'] and bomb.strikes==0
        assert moves==optimal
        for depth in range(1,6):
            probe=Bomb(seed,'hard',keystone_depth=depth)
            s=probe.current()['state']; trace=keystone.trace(s,probe.edge)
            assert len(s['keys'])==len(set(s['keys']))==4 and all(0<=k<=99 for k in s['keys'])
            assert len(s['steps'])==len(trace['steps'])==depth
            assert trace['steps'][0]['input']==0
            assert all(a['output']==b['input'] for a,b in zip(trace['steps'],trace['steps'][1:]))
            assert probe.apply('keystone:'+str(trace['key_position']))['correct']
            assert probe.defused
    assert seen==set(range(1,10))


def test_wall_bump_and_legal_detour_have_distinct_verdicts():
    bomb=Bomb(17); m=bomb.current(); state=m['state']; layout=labyrinth.layout_for(state['markers'])
    # Find a cell with at least two open neighbors so one is a legal detour.
    distance=labyrinth.distances(layout,state['exit'])
    cell=next(c for c in distance if c!=tuple(state['exit']) and sum(labyrinth.legal(layout,c,a) for a in labyrinth.DIRECTIONS)>=2)
    state['cell']=list(cell)
    bump=next(a for a in labyrinth.DIRECTIONS if not labyrinth.legal(layout,cell,a))
    result=bomb.apply('move:'+bump)
    assert not result['move_legal'] and not result['on_shortest_path']
    assert bomb.strikes==1 and state['cell']==list(cell)
    detour=next(a for a in labyrinth.DIRECTIONS if labyrinth.legal(layout,cell,a) and distance[labyrinth.destination(cell,a)]>distance[cell])
    result=bomb.apply('move:'+detour)
    assert result['correct'] and result['move_legal'] and not result['on_shortest_path']
    assert bomb.strikes==1
    assert len(state['moves'])==2 and state['moves'][0]['legal'] is False


def test_maze_view_does_not_expose_selected_walls_or_shortest_route():
    bomb=Bomb(11)
    view=bomb.view()
    assert set(view['state'])=={'markers','cell','exit','moves'}
    assert 'Layout 1:' in view['manual'] and 'Layout 9:' in view['manual']
    assert len(view['manual'].split('Walls:'))==10
    assert not {'passages','walls','optimal_moves','oracle_trace'} & view['state'].keys()
    assert [a.description for a in bomb.legal()]==['move up','move down','move left','move right']

EDGE={'serial':'ABC124','batteries':3,'indicators':{'NOVA':True,'RAY':False},'ports':['fiber']}
KEYS=[2,9,17,30]
EXPECTED={'DIGIT_TIDE':19,'LAMP_FOLD':25,'CELL_TAX':6,'KEY_FEED':14,'PRIME_TURN':13,'PORT_WEAVE':37,
          'NOVA_MIRROR':87,'ODD_ANCHOR':17,'HIGH_KEY':40,'RAY_SWITCH':29,'DIGIT_FLIP':210,'VOWEL_LIFT':25,
          'FIBER_FORK':27,'KEY_GAP':40,'QUARTER_ECHO':4,'LAMP_COUNT':18}

@pytest.mark.parametrize('rule,expected',list(EXPECTED.items()))
def test_independent_keystone_rule_examples(rule,expected):
    assert keystone.apply_step(rule,12,KEYS,EDGE)==expected


def test_all_keystone_rule_branches_and_prime_boundaries():
    assert set(EXPECTED)==set(keystone.RULES) and len(keystone.RULES)>=12
    e={**EDGE,'indicators':{'NOVA':False,'RAY':False}}
    assert keystone.apply_step('LAMP_FOLD',12,KEYS,e)==19
    assert keystone.apply_step('NOVA_MIRROR',12,KEYS,e)==23
    assert keystone.apply_step('PRIME_TURN',13,KEYS,EDGE)==16
    assert keystone.apply_step('ODD_ANCHOR',13,KEYS,EDGE)==18
    assert keystone.apply_step('RAY_SWITCH',12,KEYS,{**EDGE,'indicators':{'NOVA':True,'RAY':True}})==62
    assert keystone.apply_step('VOWEL_LIFT',12,KEYS,{**EDGE,'serial':'BCX124'})==3
    assert keystone.apply_step('FIBER_FORK',12,KEYS,{**EDGE,'ports':[]})==18
    assert keystone.apply_step('CELL_TAX',1,KEYS,{**EDGE,'batteries':4,'ports':['fiber','copper','optic']})==985
    assert [x for x in range(100) if keystone.is_prime(x)]==[2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97]


def test_chain_trace_is_exact_and_stays_out_of_prompt():
    state={'keys':KEYS,'depth':5,'steps':['DIGIT_TIDE','CELL_TAX','LAMP_FOLD','KEY_FEED','PRIME_TURN']}
    trace=keystone.trace(state,EDGE)
    assert [x['output'] for x in trace['steps']]==[7,1,3,33,36]
    assert trace['key_position']==1
    bomb=Bomb(5,'hard'); module=next(m for m in bomb.modules if m['kind']=='keystone')
    depths=[]
    while not module['solved']:
        view=bomb.view(module); assert 'oracle_trace' not in json.dumps(view) and 'initial_value' not in view['state']
        assert [a.description for a in bomb.legal(module)]==['press key 1','press key 2','press key 3','press key 4']
        depths.append(view['state']['depth'])
        result=bomb.apply(bomb.answer(module)[0],module['id'])
        assert len(result['oracle_trace']['steps'])==view['state']['depth']
    assert depths==[3,4,5]


def test_wrong_keystone_press_is_immediate_strike_without_advancing():
    bomb=Bomb(2,keystone_depth=4); before=deepcopy(bomb.current()['state'])
    right=bomb.answer()[0]; wrong=next(a.id for a in bomb.legal() if a.id!=right)
    result=bomb.apply(wrong)
    assert not result['correct'] and bomb.strikes==1 and bomb.current()['state']==before
    assert len(result['oracle_trace']['steps'])==4


def test_module_integration_counts_and_increasing_depths():
    for difficulty,count in [('easy',6),('medium',9),('hard',10)]:
        bomb=Bomb(5,difficulty); kinds=[m['kind'] for m in bomb.modules]
        assert len(kinds)==count and 'labyrinth' in kinds
        assert ('keystone' in kinds)==(difficulty!='easy')
        if difficulty!='easy':
            depths=next(m['depths'] for m in bomb.modules if m['kind']=='keystone')
            assert len(depths)==3 and depths==sorted(set(depths))


def test_sweep_offline_one_choice_per_seed_depth_and_zero_cost(tmp_path):
    output=tmp_path/'sweep'; private=tmp_path/'private'
    status=main(['sweep','--seeds','4','--controllers','solver','random','first_option','--depths','1','2','3','4','5',
                 '--no-video','--step-seconds','0','--output',str(output),'--budget-dir',str(private)])
    assert status==0 and not private.exists()
    results=[json.loads(p.read_text()) for p in output.rglob('results.json')]
    assert len(results)==60 and all(r['actions']==1 and r['cost_usd']==0 for r in results)
    assert all(r['defused'] for r in results if r['controller']=='solver')
    report=json.loads((output/'report/report.json').read_text())
    assert len(report['groups'])==15
    for group in report['groups']:
        assert group['scenario']=='keystone_sweep' and group['attempts']==4
        metrics=group['keystone_accuracy_by_depth'][str(group['keystone_depth'])]
        assert metrics['total']==4 and metrics['random_chance']==.25
        if group['controller']=='solver': assert metrics['accuracy']==1


def test_new_metrics_in_logs_and_reports(tmp_path):
    from defuse.reports import report
    folder,result=run_attempt(8,'solver',output=tmp_path,video=False,step_seconds=0,keystone_depth=5)
    row=json.loads((folder/'actions.jsonl').read_text().splitlines()[0])
    assert row['depth']==5 and len(row['oracle_trace']['steps'])==5
    # A maze-only request cap yields one measured move, with its initial optimum retained.
    run_attempt(8,'solver',output=tmp_path,video=False,step_seconds=0,max_requests=1)
    payload=report(tmp_path)
    maze_group=next(g for g in payload['groups'] if g['scenario']=='bomb')
    assert maze_group['labyrinth']['moves_taken']==1
    assert maze_group['labyrinth']['legal_move_rate']==maze_group['labyrinth']['shortest_path_rate']==1
    assert maze_group['labyrinth']['per_maze'][0]['optimal_moves']>=8
