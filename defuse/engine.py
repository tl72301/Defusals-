"""Pure, deterministic state machine. Time is supplied explicitly by the runner."""
from copy import deepcopy
from dataclasses import dataclass
import random
import string
from defuse.manual import GLYPH_COLUMNS, WORDS, SECTIONS
from defuse.modules.rules import COLORS, correct, display
from defuse.modules import labyrinth, keystone

@dataclass(frozen=True)
class Action:
    id: str
    description: str
    def as_dict(self): return {'id':self.id, 'description':self.description}

PROBE_KINDS = ('wires','button','glyph','echo','recall','lexicon','keystone','labyrinth')


class Bomb:
    def __init__(self, seed, difficulty='medium', seconds=180, strike_limit=3, keystone_depth=None, only=None):
        if difficulty not in ('easy','medium','hard'): raise ValueError('difficulty must be easy, medium, or hard')
        if seconds <= 0 or strike_limit < 1: raise ValueError('positive countdown and strike limit required')
        self.seed, self.difficulty, self.duration, self.strike_limit = seed, difficulty, seconds, strike_limit
        self.keystone_depth = keystone_depth
        self.rng = random.Random(seed)
        self.interrupt_rng = random.Random(f'{seed}:interrupt')
        r = self.rng
        self.edge = {'serial': ''.join(r.choices(string.ascii_uppercase,k=3))+''.join(r.choices(string.digits,k=3)),
                     'batteries':r.randrange(5), 'indicators':{x:bool(r.getrandbits(1)) for x in ['NOVA','RAY']},
                     'ports':r.sample(['fiber','copper','optic'],r.randrange(4))}
        # Rule puzzles first, then Keystone, with the spatial Labyrinth last, so one weak puzzle type
        # cannot use up the strikes before the others are tried.
        kinds = ['wires','button','glyph','echo','recall']
        if difficulty != 'easy': kinds += ['lexicon','interrupt']
        if difficulty == 'hard': kinds += ['wires']
        kinds += ([] if difficulty=='easy' else ['keystone']) + ['labyrinth']
        if keystone_depth is not None: kinds = ['keystone']
        if only is not None:
            if only not in PROBE_KINDS: raise ValueError(f'--only must be one of {", ".join(PROBE_KINDS)}')
            kinds = [only]
        self.modules = [self._make(k,i) for i,k in enumerate(kinds)]
        self.elapsed, self.strikes = 0.0, 0
        self.events = []

    def _make(self,k,i):
        r = self.rng
        metadata = {}
        if k == 'labyrinth':
            s, optimal = labyrinth.make_state(r)
            metadata['optimal_moves'] = optimal
        elif k == 'keystone':
            depths = [self.keystone_depth] if self.keystone_depth is not None else ([3,4,5] if self.difficulty=='hard' else [1,2,3])
            s = keystone.make_state(r, depths[0])
            metadata['depths'] = depths
        elif k == 'wires': s = {'wires':r.choices(COLORS,k=r.randint(3,6))}
        elif k == 'button':
            s = {'color':r.choice(COLORS), 'label':r.choice(['DRIFT','BLOOM','TETHER']), 'held':False}
        elif k == 'glyph': s = {'glyphs':r.sample(r.choice(GLYPH_COLUMNS),4), 'pressed':[]}
        elif k == 'echo': s = {'stage':1,'flashes':[r.choice(COLORS)],'cursor':0}
        elif k == 'recall': s = {'stage':1,'screen':r.randint(1,4),'labels':r.sample([1,2,3,4],4),'history':[]}
        elif k == 'lexicon':
            while True:
                word = r.choice(WORDS)
                dials = [r.sample([c]+r.sample([x for x in string.ascii_uppercase if x!=c],2),3) for c in word]
                if sum(all(w[j] in dials[j] for j in range(4)) for w in WORDS)==1: break
            s = {'dials':dials,'indices':[r.randrange(3) for _ in range(4)],'cursor':0}
        else: s = {'active':False,'next_at':self.interrupt_rng.uniform(25,40),'deadline':None,'pressure':0,'demands':0}
        return {'id':f'{k}-{i+1}','kind':k,'solved':False,'state':s,**metadata}

    @property
    def remaining(self): return max(0., self.duration-self.elapsed)
    @property
    def defused(self):
        return self.remaining > 0 and self.strikes < self.strike_limit and all(m['solved'] or (m['kind']=='interrupt' and not m['state']['active']) for m in self.modules)
    @property
    def done(self): return self.defused or self.remaining <= 0 or self.strikes >= self.strike_limit
    @property
    def solved_count(self): return sum(m['solved'] or (m['kind']=='interrupt' and self.defused) for m in self.modules)

    def advance(self, seconds):
        if seconds < 0: raise ValueError('time cannot move backwards')
        if self.done: return
        target = min(self.duration, self.elapsed+seconds)
        for m in self.modules:
            if m['kind'] != 'interrupt': continue
            s = m['state']
            while not self.done:
                when = s['deadline'] if s['active'] else s['next_at']
                if when > target: break
                self.elapsed = when
                if s['active']:
                    self.strikes += 1
                    s.update(active=False, deadline=None, next_at=when+self.interrupt_rng.uniform(25,40))
                    self.events.append({'type':'missed_interrupt','at':when,'module':m['id'],'strikes':self.strikes,'state':deepcopy(s)})
                else:
                    s.update(active=True, deadline=when+10, pressure=self.interrupt_rng.randint(0,100), demands=s['demands']+1)
                    self.events.append({'type':'interrupt','at':when,'module':m['id'],'strikes':self.strikes,'state':deepcopy(s)})
                if self.done: return
        self.elapsed = target

    def current(self):
        if self.done: return None
        for m in self.modules:
            if m['kind']=='interrupt' and m['state']['active']: return m
        return next(m for m in self.modules if m['kind']!='interrupt' and not m['solved'])

    def legal(self, module=None):
        m = module or self.current()
        if not m: return []
        k,s = m['kind'],m['state']
        if k=='labyrinth': return [Action('move:'+direction,'move '+direction) for direction in labyrinth.DIRECTIONS]
        if k=='keystone': return [Action(f'keystone:{i}',f'press key {i}') for i in range(1,5)]
        if k=='wires': return [Action(f'cut:{i}',f'cut wire {i+1} ({c})') for i,c in enumerate(s['wires'])]
        if k=='button': return [Action('release','release button now'),Action('wait','wait 0.2 seconds')] if s['held'] else [Action('tap','press and release button'),Action('hold','hold button')]
        if k=='glyph': return [Action('glyph:'+g,'press glyph '+g) for g in s['glyphs']]
        if k=='echo': return [Action('color:'+c,'press '+c) for c in COLORS]
        if k=='recall': return [Action(f'key:{i+1}',f'press position {i+1} (label {v})') for i,v in enumerate(s['labels'])]
        if k=='lexicon': return [Action('cycle',f'cycle dial {s["cursor"]+1} forward once'),Action('lock',f'lock dial {s["cursor"]+1}')]
        return [Action('yes','vent pressure: yes'),Action('no','vent pressure: no')]

    def answer(self, module=None):
        m = module or self.current()
        return correct(m['kind'],m['state'],self.edge,self.strikes,self.remaining)

    def view(self, module=None):
        m = module or self.current()
        if not m: return None
        state = deepcopy(m['state'])
        if m['kind'] == 'lexicon':   # what each dial window shows, as a player would read it
            state['showing'] = [dial[i] for dial, i in zip(state['dials'], state['indices'])]
        return deepcopy({'edgework':self.edge,'time_left':self.remaining,'display':display(self.remaining),'strikes':self.strikes,
                         'module_id':m['id'],'module_type':m['kind'],'state':state,'manual':SECTIONS[m['kind']]})

    def snapshot(self):
        return deepcopy({'time_left':self.remaining,'elapsed':self.elapsed,'strikes':self.strikes,'edgework':self.edge,'modules':self.modules,
                         'defused':self.defused,'done':self.done,'solved_count':self.solved_count})

    def apply(self, action, module_id=None):
        if self.done: return {'correct':False,'verdict':'terminal','right_action':None,'rule':None}
        m = self.current() if module_id is None else next(x for x in self.modules if x['id']==module_id)
        if m['solved'] or (m['kind']=='interrupt' and not m['state']['active']):
            return {'correct':False,'verdict':'expired','right_action':None,'rule':None}
        right, rule = self.answer(m)
        ok = action == right
        evidence = {}
        if m['kind']=='labyrinth':
            s = m['state']; layout = labyrinth.layout_for(s['markers'])
            direction = action.split(':',1)[1] if isinstance(action,str) and action.startswith('move:') else None
            cell = tuple(s['cell']); distance = labyrinth.distances(layout,s['exit'])
            ok = direction in labyrinth.DIRECTIONS and labyrinth.legal(layout,cell,direction)
            target = labyrinth.destination(cell,direction) if ok else cell
            evidence = {'move_legal':ok,'on_shortest_path':bool(ok and distance[target]==distance[cell]-1),
                        'optimal_remaining_before':distance[cell],'optimal_remaining_after':distance[target],
                        'maze_layout':layout['id']}
            s['moves'].append({'action':direction,'from':list(cell),'to':list(target),'legal':ok})
        elif m['kind']=='keystone':
            evidence = {'depth':m['state']['depth'],'oracle_trace':keystone.trace(m['state'],self.edge)}
        if not ok:
            self.strikes += 1
            if m['kind']=='interrupt':
                m['state'].update(active=False,deadline=None,next_at=self.elapsed+self.interrupt_rng.uniform(25,40))
        else:
            k,s = m['kind'],m['state']
            if k=='labyrinth':
                s['cell']=list(target); m['solved']=s['cell']==s['exit']
            elif k=='keystone':
                history=s['history']+[{'stage':s['stage'],'depth':s['depth'],'key_position':evidence['oracle_trace']['key_position']}]
                if s['stage']==len(m['depths']): m['solved']=True
                else: m['state']=keystone.make_state(self.rng,m['depths'][s['stage']],s['stage']+1,history)
            elif k=='wires': m['solved']=True
            elif k=='button':
                if action=='hold': s.update(held=True,strip=self.rng.choice(['amber','teal','white']))
                elif action!='wait': m['solved']=True; s['held']=False
            elif k=='glyph':
                s['pressed'].append(action.split(':',1)[1]); m['solved']=len(s['pressed'])==4
            elif k=='echo':
                s['cursor']+=1
                if s['cursor']==len(s['flashes']):
                    if s['stage']==3: m['solved']=True
                    else: s.update(stage=s['stage']+1,cursor=0,flashes=s['flashes']+[self.rng.choice(COLORS)])
            elif k=='recall':
                p=int(action.split(':')[1]); s['history'].append({'stage':s['stage'],'position':p,'label':s['labels'][p-1]})
                if s['stage']==5: m['solved']=True
                else: s.update(stage=s['stage']+1,screen=self.rng.randint(1,4),labels=self.rng.sample([1,2,3,4],4))
            elif k=='lexicon':
                i=s['cursor']
                if action=='cycle': s['indices'][i]=(s['indices'][i]+1)%3
                else: s['cursor']+=1; m['solved']=s['cursor']==4
            elif k=='interrupt': s.update(active=False,deadline=None,next_at=self.elapsed+self.interrupt_rng.uniform(25,40))
        return {'correct':ok,'verdict':'progress' if ok else 'strike','right_action':right,'rule':rule,**evidence}
