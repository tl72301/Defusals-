from copy import deepcopy
import random
import pytest
from defuse.engine import Bomb
from defuse.manual import GLYPH_COLUMNS, WORDS
from defuse.modules.rules import correct, display
from defuse.solver import choose

@pytest.mark.parametrize('difficulty',['easy','medium','hard'])
def test_solver_thousand_seeds_each_difficulty(difficulty):
    seeds=random.Random(49271).sample(range(2**31),1000)
    for seed in seeds:
        bomb=Bomb(seed,difficulty)
        for step in range(1000):
            if bomb.done: break
            legal=bomb.legal()
            assert 2<=len(legal)<=8, (seed,difficulty)
            action=choose(bomb)
            assert action in [a.id for a in legal]
            assert bomb.apply(action)['correct']
            bomb.advance(.2)
        assert bomb.defused and bomb.strikes==0, (seed,difficulty,bomb.snapshot())

@pytest.mark.parametrize('seed',range(20))
def test_determinism(seed):
    a,b=Bomb(seed,'hard'),Bomb(seed,'hard')
    while not a.done:
        assert a.snapshot()==b.snapshot()
        action=choose(a)
        assert a.apply(action)==b.apply(action)
        a.advance(.2); b.advance(.2)
    assert a.snapshot()==b.snapshot()

@pytest.mark.parametrize('kind',['wires','button','glyph','echo','recall','lexicon','interrupt'])
def test_wrong_actions_strike_immediately(kind):
    b=Bomb(9,'hard'); m=next(m for m in b.modules if m['kind']==kind)
    if kind=='interrupt': m['state'].update(active=True,pressure=80,deadline=10)
    right=b.answer(m)[0]; wrong=next(a.id for a in b.legal(m) if a.id!=right)
    before=deepcopy(m['state'])
    result=b.apply(wrong,m['id'])
    assert not result['correct'] and b.strikes==1
    if kind=='interrupt': assert not m['state']['active']
    else: assert m['state']==before

EDGE={'serial':'ABC124','batteries':3,'indicators':{'NOVA':True,'RAY':False},'ports':['fiber']}
def oracle(kind,state,edge=None,strikes=0,remaining=180): return correct(kind,state,edge or EDGE,strikes,remaining)

@pytest.mark.parametrize('wires,serial,action,rule',[
    (['amber','amber','plum'],'BCX124','cut:1','amber_even'),
    (['amber','amber','plum'],'ABC123','cut:1','no_teal_vowel'),
    (['white','plum','white'],'BCX123','cut:1','match_ends'),
    (['teal','plum','white','teal'],'ABC124','cut:1','match_ends'),
    (['amber','plum','teal'],'ABC124','cut:2','last'),
])
def test_wire_manual_examples(wires,serial,action,rule):
    assert oracle('wires',{'wires':wires},{**EDGE,'serial':serial})==(action,'wires.'+rule)

@pytest.mark.parametrize('label,color,batteries,nova,expected,rule',[
    ('DRIFT','teal',3,False,'tap','drift'),('DRIFT','teal',2,False,'hold','hold'),
    ('BLOOM','plum',0,True,'tap','nova'),('BLOOM','plum',4,False,'hold','hold'),
    ('DRIFT','plum',4,True,'tap','drift'),
])
def test_button_initial_manual(label,color,batteries,nova,expected,rule):
    edge={**EDGE,'batteries':batteries,'indicators':{**EDGE['indicators'],'NOVA':nova}}
    assert oracle('button',{'held':False,'label':label,'color':color},edge)==(expected,'button.'+rule)

@pytest.mark.parametrize('strip,release,wait',[('amber',133,142),('teal',166,142),('white',180,682)])
def test_all_button_strip_rules(strip,release,wait):
    s={'held':True,'strip':strip}
    assert oracle('button',s,remaining=release)==('release','button.release_'+strip)
    assert oracle('button',s,remaining=wait)==('wait','button.wait_'+strip)

def test_button_uses_arrival_time():
    b=Bomb(1); m=next(m for m in b.modules if m['kind']=='button'); m['state'].update(held=True,strip='teal'); b.elapsed=14 # 02:46
    assert b.answer(m)[0]=='release'
    b.advance(1.1)
    assert not b.apply('release',m['id'])['correct']
    assert b.strikes==1

@pytest.mark.parametrize('column',range(3))
def test_glyph_columns(column):
    c=GLYPH_COLUMNS[column]; s={'glyphs':[c[4],c[0],c[5],c[2]],'pressed':[]}
    for g in [c[0],c[2],c[4],c[5]]:
        assert oracle('glyph',s)==('glyph:'+g,'glyph.column'+str(column)); s['pressed'].append(g)

@pytest.mark.parametrize('serial,expected', [('BCD123',[
    ['amber','teal','plum','white'],['teal','plum','white','amber'],['plum','white','amber','teal']]),('ABC123',[
    ['teal','plum','white','amber'],['plum','white','amber','teal'],['white','amber','teal','plum']])])
def test_echo_complete_table(serial,expected):
    colors=['amber','teal','plum','white']
    for strikes,row in enumerate(expected):
        for i,color in enumerate(colors):
            assert oracle('echo',{'flashes':[color],'cursor':0},{**EDGE,'serial':serial},strikes)[0]=='color:'+row[i]

@pytest.mark.parametrize('stage,screen,batteries,expected,clause',[
    (1,3,3,3,'stage1'), (2,1,3,4,'stage2'),
    (3,2,3,2,'stage3_even'),(3,1,3,1,'stage3_odd'),
    (4,3,3,2,'stage4_high'),(4,2,3,1,'stage4_low'),
    (5,1,3,3,'stage5_batteries'),(5,4,1,4,'stage5_few'),
])
def test_recall_all_manual_clauses(stage,screen,batteries,expected,clause):
    s={'stage':stage,'screen':screen,'labels':[4,1,2,3],
       'history':[{'position':2,'label':3},{'position':4,'label':1},{'position':1,'label':4},{'position':3,'label':2}]}
    assert oracle('recall',s,{**EDGE,'batteries':batteries})==(f'key:{expected}','recall.'+clause)

def test_lexicon_cycles_then_locks_unique_word():
    s={'dials':[['X','M','Z'],['X','I','Z'],['X','S','Z'],['X','T','Z']],'indices':[0,0,0,0],'cursor':0}
    for i in range(4):
        s['cursor']=i
        assert oracle('lexicon',s)==('cycle','lexicon.cycle')
        s['indices'][i]=1
        assert oracle('lexicon',s)==('lock','lexicon.lock')

@pytest.mark.parametrize('pressure,lit,ports,expected,clause',[
    (59,False,['fiber'],'no','low'),(60,False,[],'yes','unlit'),
    (60,True,['fiber'],'yes','fiber'),(100,True,[],'no','lit_no_fiber')])
def test_interrupt_clauses(pressure,lit,ports,expected,clause):
    e={**EDGE,'indicators':{**EDGE['indicators'],'RAY':lit},'ports':ports}
    assert oracle('interrupt',{'pressure':pressure},e)==(expected,'interrupt.'+clause)

def test_interrupt_deadline_preemption_and_rearming():
    b=Bomb(1); m=next(x for x in b.modules if x['kind']=='interrupt'); first=m['state']['next_at']; assert 25<=first<=40
    b.advance(first)
    assert b.current()==m and m['state']['active']
    b.advance(10)
    assert b.strikes==1 and not m['state']['active']
    assert b.events[-1]['type']=='missed_interrupt'
    assert 25<=m['state']['next_at']-b.elapsed<=40
    b.advance(m['state']['next_at']-b.elapsed)
    assert b.apply(b.answer()[0])['correct']
    assert not m['state']['active']
    b.advance(130)
    assert b.strikes==3 and b.done

def test_interrupt_prevents_win_until_demand_cleared():
    b=Bomb(4); m=next(x for x in b.modules if x['kind']=='interrupt'); b.advance(m['state']['next_at'])
    for other in b.modules:
        if other is not m: other['solved']=True
    assert not b.defused
    b.apply(b.answer()[0]); assert b.defused and b.solved_count==9

def test_countdown_and_strike_limit():
    b=Bomb(1,seconds=1); b.advance(1); assert b.done and not b.defused
    b=Bomb(1)
    for _ in range(3): b.apply('not-legal')
    assert b.done and b.strikes==3
    assert b.apply('not-legal')['verdict']=='terminal'

def test_view_never_contains_oracle_answers():
    b=Bomb(1,'hard')
    while not b.done:
        view=b.view(); assert not {'right_action','rule','correct','target'} & view.keys()
        assert 'history' in view['state'] if view['module_type']=='recall' else True
        b.apply(b.answer()[0]); b.advance(.2)
