"""Pillow replay at the recorded wall-clock pace, piped into H.264 ffmpeg."""
from functools import lru_cache
from copy import deepcopy
import json
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
from defuse.modules.rules import display
from defuse.modules import labyrinth

WIDTH,HEIGHT,FPS=1280,720,30
PALETTE={'amber':'#f8ba55','teal':'#54d3be','plum':'#b39bfa','white':'#f4f3e9'}
NAMES={'wires':'THREAD ARRAY','button':'PULSE SEAL','glyph':'SIGIL RACK','echo':'TINT ECHO','recall':'LEDGER KEYS','lexicon':'WORD LOOM','interrupt':'RELIEF WATCH'}
NAMES.update(labyrinth='LABYRINTH',keystone='KEYSTONE')

def ffmpeg_binary():
    system=shutil.which('ffmpeg')
    if system: return system
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

@lru_cache(maxsize=12)
def font(size):
    for name in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']:
        if Path(name).exists(): return ImageFont.truetype(name,size)
    return ImageFont.load_default(size=size)

def text(draw,xy,value,size=16,fill='#cbd6dc'):
    draw.text(xy,str(value),font=font(size),fill=fill)

def frame(state,manifest,options=(),answer=None,correct=None,focus=None,wall=0.,thinking=False):
    im=Image.new('RGB',(WIDTH,HEIGHT),'#10191f'); d=ImageDraw.Draw(im)
    d.rounded_rectangle((24,22,1256,174),radius=18,fill='#1a2a33')
    text(d,(44,37),'DEFUSE × DECISIONS',30,'#f4f3e9')
    text(d,(46,79),'ORIGINAL PUZZLES / RECORDED REASONING',13,'#7d9da8')
    text(d,(46,118),f'SEED {manifest["seed"]}   /   {manifest["difficulty"].upper()}   /   {manifest["controller"].upper()}',17)
    text(d,(651,40),display(state['time_left']),66,'#54d3be' if not state['done'] else ('#54d3be' if state['defused'] else '#ff786b'))
    for i in range(3):
        d.ellipse((988+i*66,59,1014+i*66,85),fill='#ff786b' if i<state['strikes'] else '#34434b')
    text(d,(984,101),f'{state["strikes"]} / 3 STRIKES',18)
    mode='PAUSED — JUDGMENT ONLY' if manifest['timing']=='paused' else 'REALTIME — CLOCK RUNNING'
    text(d,(42,183),mode,16,'#f8ba55' if manifest['timing']=='paused' else '#54d3be')
    columns=5 if len(state['modules'])>8 else 4
    card_width=860//columns-14
    board_draw=d
    for i,m in enumerate(state['modules']):
        card=Image.new('RGB',(203,189),'#10191f'); d=ImageDraw.Draw(card)
        x=0; y=0; s=m['state']; k=m['kind']
        solved=m['solved'] or (k=='interrupt' and state['defused'])
        active=m['id']==focus
        d.rounded_rectangle((x,y,x+201,y+187),radius=12,fill='#20343d' if active else '#182830',outline='#54d3be' if solved else ('#f8ba55' if active else '#32434c'),width=2)
        text(d,(x+12,y+12),NAMES[k],14,'#54d3be' if solved else '#f4f3e9')
        text(d,(x+12,y+36),'CLEARED' if solved else ('ACTIVE' if active else 'STANDBY'),10,'#54d3be' if solved else '#78959f')
        if k=='labyrinth':
            layout=labyrinth.layout_for(s['markers']); unit=19; ox=x+44; oy=y+60
            def center(cell): return (ox+(cell[1]-.5)*unit,oy+(cell[0]-.5)*unit)
            for move in s['moves']:
                if move['legal']: d.line((*center(move['from']),*center(move['to'])),fill='#407f7b',width=4)
            d.rectangle((ox,oy,ox+6*unit,oy+6*unit),outline='#b2c6ce',width=2)
            for row in range(1,7):
                for col in range(1,7):
                    xx=ox+(col-1)*unit; yy=oy+(row-1)*unit
                    if col<6 and not labyrinth.legal(layout,(row,col),'right'): d.line((xx+unit,yy,xx+unit,yy+unit),fill='#b2c6ce',width=2)
                    if row<6 and not labyrinth.legal(layout,(row,col),'down'): d.line((xx,yy+unit,xx+unit,yy+unit),fill='#b2c6ce',width=2)
            for marker in s['markers']:
                xx,yy=center(marker); d.ellipse((xx-6,yy-6,xx+6,yy+6),outline='#f4f3e9',width=1)
            xx,yy=center(s['exit']); d.rectangle((xx-5,yy-5,xx+5,yy+5),outline='#54d3be',width=2)
            xx,yy=center(s['cell']); d.ellipse((xx-4,yy-4,xx+4,yy+4),fill='#f8ba55')
        elif k=='keystone':
            text(d,(x+15,y+58),f'DEPTH {s["depth"]}   /   STAGE {s["stage"]}',14,'#f8ba55')
            for j,number in enumerate(s['keys']):
                xx=x+15+(j%2)*87; yy=y+84+(j//2)*45
                d.rounded_rectangle((xx,yy,xx+75,yy+36),radius=5,fill='#314b57')
                text(d,(xx+8,yy+8),f'{j+1} / {number:02d}',16)
        elif k=='wires':
            for j,c in enumerate(s['wires']):
                yy=y+67+j*17; text(d,(x+12,yy-8),j+1,12); d.line((x+40,yy,x+179,yy),fill=PALETTE[c],width=6)
        elif k=='button':
            d.ellipse((x+53,y+62,x+147,y+151),fill=PALETTE[s['color']]); text(d,(x+68,y+96),s['label'],13,'#10191f')
            if s['held'] and not solved:
                d.rectangle((x+167,y+66,x+180,y+149),fill=PALETTE[s['strip']]); text(d,(x+65,y+160),'HELD',12)
        elif k=='glyph':
            for j,g in enumerate(s['glyphs']):
                text(d,(x+14,y+61+j*27),('✓ ' if g in s['pressed'] else '◇ ')+g,14,'#54d3be' if g in s['pressed'] else '#cbd6dc')
        elif k=='echo':
            text(d,(x+13,y+64),f'STAGE {s["stage"]} / 3',17)
            for j,c in enumerate(s['flashes']):
                xx=x+17+j*53; d.rounded_rectangle((xx,y+99,xx+37,y+136),radius=8,fill=PALETTE[c])
                if j==s['cursor']: d.line((xx,y+148,xx+37,y+148),fill='#f4f3e9',width=3)
        elif k=='recall':
            text(d,(x+13,y+62),f'SCREEN {s["screen"]}  /  STEP {s["stage"]}',16)
            for j,label in enumerate(s['labels']):
                xx=x+13+j*45; d.rounded_rectangle((xx,y+93,xx+36,y+128),radius=5,fill='#314b57'); text(d,(xx+11,y+99),label,18)
            text(d,(x+13,y+144),'H: '+' '.join(f'{h["position"]}:{h["label"]}' for h in s['history']),11)
        elif k=='lexicon':
            for j,dial in enumerate(s['dials']):
                xx=x+15+j*45; text(d,(xx,y+85),dial[s['indices'][j]],29,'#54d3be' if j<s['cursor'] else '#f4f3e9')
                text(d,(xx,y+130),''.join(dial),10)
                if j==s['cursor']: d.line((xx,y+120,xx+24,y+120),fill='#f8ba55',width=2)
        else:
            text(d,(x+14,y+73),'DEMAND' if s['active'] else 'MONITORING',19,'#ff786b' if s['active'] else '#78959f')
            if s['active']:
                text(d,(x+14,y+109),f'PRESSURE {s["pressure"]}',17)
                text(d,(x+14,y+142),f'{max(0,s["deadline"]-state["elapsed"]):.1f}s to respond',13)
        im.paste(card.resize((card_width,189),Image.Resampling.LANCZOS),(28+(i%columns)*(860//columns),220+(i//columns)*203))
        d=board_draw
    d.rounded_rectangle((909,218,1254,610),radius=12,fill='#1a2a33')
    text(d,(929,236),'DECISION CHANNEL',18,'#f4f3e9')
    text(d,(929,268),'REQUEST IN FLIGHT' if thinking else 'ACTION RECEIVED',11,'#f8ba55' if thinking else '#78959f')
    for j,o in enumerate(options):
        label=f'{o["value"]}  {o["description"]}'
        selected=answer and answer.get('choice')==o['value'] and not thinking
        if selected: d.rounded_rectangle((922,296+j*30,1241,324+j*30),radius=4,fill='#285648' if correct else '#6e3637')
        text(d,(931,300+j*30),label,13,'#ffffff' if selected else '#b2c6ce')
    if answer and not thinking:
        conf=answer.get('confidence'); confidence='—' if conf is None else f'{conf:.3f}'
        text(d,(929,551),f'CONF {confidence}   /   {answer.get("latency",0)*1000:.0f} ms',14)
        text(d,(929,578),answer.get('error') or ('CORRECT' if correct else 'STRIKE / NO PROGRESS'),13,'#54d3be' if correct else '#ff786b')
    e=state['edgework']; lights='  '.join(f'{k}:{"ON" if v else "OFF"}' for k,v in e['indicators'].items())
    text(d,(36,639),f'SERIAL {e["serial"]}   /   BAT {e["batteries"]}   /   {lights}   /   PORTS {", ".join(e["ports"]) or "NONE"}',15)
    status='DEFUSED' if state['defused'] else ('ATTEMPT ENDED' if state['done'] else f'{state["solved_count"]}/{len(state["modules"])} MODULES')
    text(d,(36,676),status,16,'#54d3be' if state['defused'] else '#f4f3e9')
    text(d,(842,676),f'WALL {wall:07.2f}s   ·   TEXT INPUT ONLY',14,'#78959f')
    return im

def read_jsonl(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x]

def render_run(folder):
    folder=Path(folder); manifest=json.loads((folder/'manifest.json').read_text()); result=json.loads((folder/'results.json').read_text()); actions=read_jsonl(folder/'actions.jsonl')
    events=read_jsonl(folder/'events.jsonl') if (folder/'events.jsonl').exists() else []
    timed_events=[]
    for event in events:
        if event['type'] not in ('interrupt','missed_interrupt'): continue
        event=deepcopy(event)
        anchor=next((a for a in reversed(actions) if a['game_after']<=event['at']),None)
        event['replay_at']=(anchor['decision_at']+event['at']-anchor['game_after']) if anchor else event['at']
        # Backward-compatible replay of recordings made before event state snapshots were added.
        if 'state' not in event and event['type']=='interrupt':
            event['state']=next((deepcopy(m['state']) for a in actions for m in a['before']['modules']
                                 if m['id']==event['module'] and m['state'].get('deadline')==event['at']+10),
                                {'active':True,'deadline':event['at']+10,'pressure':'?','next_at':event['at'],'demands':1})
        timed_events.append(event)
    duration=max(1/FPS,result['wall_duration']); count=max(1,math.ceil(duration*FPS)); target=folder/'gameplay.mp4'
    cmd=[ffmpeg_binary(),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{WIDTH}x{HEIGHT}','-r',str(FPS),'-i','-',
         '-an','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(target)]
    index=-1; cached_key=None; pixels=None
    with open(folder/'render.log','w') as error:
        process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=error)
        try:
            for i in range(count):
                t=i/FPS
                while index+1<len(actions) and actions[index+1]['request_at']<=t: index+=1
                a=actions[index] if index>=0 else None
                if i==count-1 and actions: a=actions[-1]; index=len(actions)-1
                thinking=bool(a and t<a['decision_at'])
                state=deepcopy((a['before'] if thinking else a['after']) if a else manifest['initial_state'])
                snapshot_game_time=state['elapsed']
                if a:
                    base=a['request_at'] if thinking else a['decision_at']
                    if manifest['timing']=='realtime' or not thinking:
                        dt=max(0,t-base); state['time_left']=max(0,state['time_left']-dt); state['elapsed']+=dt
                event_revision=0
                for event in timed_events:
                    if event['at']>snapshot_game_time and event['replay_at']<=t:
                        module=next(m for m in state['modules'] if m['id']==event['module'])
                        if 'state' in event: module['state']=deepcopy(event['state'])
                        elif event['type']=='missed_interrupt': module['state']['active']=False
                        if 'strikes' in event: state['strikes']=event['strikes']
                        event_revision+=1
                        if state['strikes']>=3:
                            state.update(done=True,defused=False,elapsed=event['at'],time_left=max(0,manifest['limits']['seconds']-event['at']))
                if i==count-1: state=result['final_state']; thinking=False
                key=(index,thinking,display(state['time_left']),int(t*5),event_revision,i==count-1)
                if key!=cached_key:
                    pixels=frame(state,manifest,a['options'] if a else [],a['answer'] if a else None,a['correct'] if a else None,a['module_id'] if a else None,t,thinking).tobytes(); cached_key=key
                process.stdin.write(pixels)
            process.stdin.close(); status=process.wait()
            if status: raise RuntimeError('ffmpeg rendering failed; see render.log')
        except BaseException:
            process.kill(); process.wait(); raise
    return {'frames':count,'fps':FPS,'duration':count/FPS,'width':WIDTH,'height':HEIGHT,'path':'gameplay.mp4','size_bytes':target.stat().st_size,
            'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
