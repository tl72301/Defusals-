"""Run a bomb, capturing immutable requests and before/after snapshots for replay."""
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import time
import uuid
from defuse.budget import append_json, BudgetError
from defuse.decisions import Decisions, API_URL, Answer
from defuse.engine import Bomb

CONTROLLERS=('solver','random','first_option','decisions')
TIMINGS=('realtime','paused')

def code_revision():
    try:
        root=Path(__file__).resolve().parent.parent
        head=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True)
        status=subprocess.run(['git','status','--porcelain'],cwd=root,capture_output=True,text=True)
        digest=hashlib.sha256()
        for p in sorted((root/'defuse').rglob('*.py')): digest.update(str(p.relative_to(root)).encode()); digest.update(p.read_bytes())
        return {'git':head.stdout.strip() if head.returncode==0 else 'unborn','dirty':bool(status.stdout),'source_sha256':digest.hexdigest()}
    except OSError: return {'git':'unavailable'}

def shuffle_options(actions,seed,index):
    shuffle_seed=int.from_bytes(hashlib.sha256(f'{seed}:options:{index}'.encode()).digest()[:8],'big')
    order=list(actions); random.Random(shuffle_seed).shuffle(order)
    return shuffle_seed,[{'value':chr(65+i),**a.as_dict()} for i,a in enumerate(order)]

class Clock:
    def __init__(self,bomb,timing,now=time.monotonic): self.bomb,self.timing,self.now,self.last=bomb,timing,now,now()
    def sync(self):
        current=self.now(); self.bomb.advance(max(0,current-self.last)); self.last=current
    def after_request(self):
        if self.timing=='realtime': self.sync()
        else: self.last=self.now()

def run_attempt(seed,controller='solver',timing='realtime',difficulty='medium',seconds=180,output=Path('data/runs'),
                endpoint=API_URL,timeout=.6,budget=None,batch=False,category='attempt',video=True,step_seconds=.2,max_requests=300,keystone_depth=None,only=None,strikes=3,fresh_on_strike=False):
    if controller not in CONTROLLERS or timing not in TIMINGS: raise ValueError('invalid controller or timing')
    if not math.isfinite(seconds) or seconds<=0 or not math.isfinite(step_seconds) or step_seconds<0: raise ValueError('invalid timing limits')
    if max_requests<1: raise ValueError('max requests must be positive')
    bomb=Bomb(seed,difficulty,seconds,strike_limit=strikes,keystone_depth=keystone_depth,only=only,fresh_on_strike=fresh_on_strike)
    run_id=f'{seed}-{controller}-{timing}-{uuid.uuid4().hex[:8]}'
    folder=Path(output)/run_id; folder.mkdir(parents=True,exist_ok=False)
    api=Decisions(endpoint,timeout,budget,category,batch) if controller=='decisions' else None
    manifest={'schema_version':1,'run_id':run_id,'seed':seed,'difficulty':difficulty,'controller':controller,'timing':timing,
              'scenario':('keystone_sweep' if keystone_depth is not None else (f'probe:{only}' if only else 'bomb'))+('+fresh' if fresh_on_strike else ''),'keystone_depth':keystone_depth,
              'code_revision':code_revision(),'limits':{'seconds':seconds,'strikes':strikes,'timeout':timeout,'step_seconds':step_seconds,'max_requests':max_requests},
              'model':'gpt-6-luna' if api else None,'stub':api.stub if api else False,'price_per_million_input_tokens_usd':.10,
              'initial_state':bomb.snapshot(),'created_unix':time.time(),'video':{'fps':30,'width':1280,'height':720,'enabled':video}}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
    for name in ['actions.jsonl','api-usage.jsonl','events.jsonl']: (folder/name).touch()
    actions=[]; total_tokens=0; total_cost=0.; unknown=0; errors=0; reason=None
    rng=random.Random(f'{seed}:random-controller')
    start=time.monotonic(); clock=Clock(bomb,timing); event_cursor=0
    while not bomb.done and len(actions)<max_requests:
        clock.sync()
        if bomb.done: break
        m=bomb.current(); module_id=m['id']; shown=bomb.view(m); before=bomb.snapshot()
        shuffle_seed,options=shuffle_options(bomb.legal(m),seed,len(actions))
        request_at=time.monotonic()-start; game_at=bomb.elapsed
        answer=Answer(); chosen=None
        try:
            if api:
                answer=api.ask(shown,options)
                chosen=next((o['id'] for o in options if o['value']==answer.choice),None)
            else:
                t=time.monotonic()
                chosen=bomb.answer(m)[0] if controller=='solver' else (rng.choice(options)['id'] if controller=='random' else options[0]['id'])
                answer.choice=next(o['value'] for o in options if o['id']==chosen)
                answer.latency=time.monotonic()-t
        except (BudgetError,ValueError) as exc:
            reason='budget_or_configuration_blocked'; errors+=1
            append_json(folder/'events.jsonl',{'type':reason,'detail':str(exc),'wall_at':time.monotonic()-start})
            break
        clock.after_request()
        decision_at=time.monotonic()-start
        verdict=bomb.apply(chosen,module_id)
        if api:
            usage={**answer.as_dict(),'index':len(actions),'stub':api.stub}
            append_json(folder/'api-usage.jsonl',usage)
            total_tokens+=answer.input_tokens or 0; total_cost+=answer.cost_usd; unknown+=int(answer.billing_unknown); errors+=bool(answer.error)
        row={'index':len(actions),'request_at':request_at,'decision_at':decision_at,'game_at':game_at,'game_after':bomb.elapsed,
             'module_id':module_id,'module_type':m['kind'],'state_shown':shown,'before':before,'options':options,'shuffle_seed':shuffle_seed,
             'answer':answer.as_dict(),'chosen_action':chosen,**verdict,'after':bomb.snapshot()}
        if m['kind']=='keystone':
            from defuse.modules.keystone import trace
            row.setdefault('depth',shown['state']['depth'])
            row.setdefault('oracle_trace',trace(shown['state'],shown['edgework']))
        append_json(folder/'actions.jsonl',row); actions.append(row)
        for event in bomb.events[event_cursor:]: append_json(folder/'events.jsonl',{**event,'wall_at':time.monotonic()-start})
        event_cursor=len(bomb.events)
        # All controllers receive the same actuator dwell; wait literally consumes 0.2 seconds.
        if not bomb.done:
            time.sleep(.2 if chosen=='wait' else step_seconds); clock.sync()
    if not bomb.done and reason is None: reason='request_limit'
    wall_duration=time.monotonic()-start
    for event in bomb.events[event_cursor:]: append_json(folder/'events.jsonl',{**event,'wall_at':wall_duration})
    result={'run_id':run_id,'seed':seed,'controller':controller,'timing':timing,'difficulty':difficulty,'stub':api.stub if api else False,
            'scenario':manifest['scenario'],'keystone_depth':keystone_depth,
            'defused':bomb.defused,'modules_solved':bomb.solved_count,'modules_total':len(bomb.modules),'strikes':bomb.strikes,
            'time_left':bomb.remaining,'game_duration':bomb.elapsed,'wall_duration':wall_duration,'requests':len(actions) if api else 0,
            'actions':len(actions),'correct_actions':sum(a['correct'] for a in actions),'input_tokens':total_tokens,'cost_usd':total_cost,
            'billing_unknown_requests':unknown,'errors':errors,'end_reason':reason or ('defused' if bomb.defused else ('strikes' if bomb.strikes>=bomb.strike_limit else 'countdown')),
            'final_state':bomb.snapshot(),'video_status':'pending' if video else 'disabled'}
    (folder/'results.json').write_text(json.dumps(result,indent=2))
    if video:
        from defuse.render import render_run
        try:
            metadata=render_run(folder)
            result['video_status']='complete'; result['video']=metadata
        except Exception:
            result['video_status']='failed'; (folder/'results.json').write_text(json.dumps(result,indent=2)); raise
        (folder/'results.json').write_text(json.dumps(result,indent=2))
    return folder,result

def summary_line(folder,r):
    return f'seed={r["seed"]} controller={r["controller"]} timing={r["timing"]} defused={r["defused"]} modules={r["modules_solved"]}/{r["modules_total"]} strikes={r["strikes"]} left={r["time_left"]:.2f}s requests={r["requests"]} cost=${r["cost_usd"]:.7f} path={folder}'
