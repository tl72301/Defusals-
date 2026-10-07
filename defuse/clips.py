"""Bounded-size review copies and a best/worst highlight reel."""
import json
import math
from pathlib import Path
import subprocess
import tempfile
from defuse.render import ffmpeg_binary
from defuse.reports import load_runs, rank

MAX_BYTES=25_000_000

def encode(source,target,start=0.,duration=None):
    cmd=[ffmpeg_binary(),'-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',str(source)]
    if duration is not None: cmd+=['-t',str(duration)]
    cmd+=['-vf','scale=960:540','-r','30','-an','-c:v','libx264','-preset','veryfast','-b:v','1200k','-maxrate','1400k','-bufsize','2400k','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    subprocess.run(cmd,check=True,capture_output=True)
    if target.stat().st_size>=MAX_BYTES: raise RuntimeError('Clip exceeded 25 MB: '+str(target))
    return {'path':str(target),'size_bytes':target.stat().st_size,'start':start,'duration':duration}

def clips(root,output=None):
    root=Path(root); output=Path(output or root/'clips'); output.mkdir(parents=True,exist_ok=True)
    runs=load_runs(root); entries=[]; playable=[r for r in runs if (r[0]/'gameplay.mp4').exists()]
    if not playable: raise ValueError('No gameplay videos found')
    for p,r,m,a in playable:
        duration=r['video']['duration']
        # <=100 seconds at capped 1.4 Mbps, leaving ample container overhead below 25 MB.
        for i in range(max(1,math.ceil(duration/100))):
            entries.append(encode(p/'gameplay.mp4',output/f'{r["run_id"]}-part{i+1}.mp4',i*100,min(100,duration-i*100)))
    best,worst=max(playable,key=rank),min(playable,key=rank)
    with tempfile.TemporaryDirectory(prefix='defuse-highlights-') as td:
        td=Path(td)
        for label,run in [('best',best),('worst',worst)]:
            duration=run[1]['video']['duration']; encode(run[0]/'gameplay.mp4',td/f'{label}.mp4',max(0,duration-8),min(8,duration))
        (td/'concat.txt').write_text("file 'best.mp4'\nfile 'worst.mp4'\n")
        target=output/'best-and-worst.mp4'
        subprocess.run([ffmpeg_binary(),'-hide_banner','-loglevel','error','-y','-f','concat','-safe','1','-i',str(td/'concat.txt'),'-c','copy','-movflags','+faststart',str(target)],check=True,capture_output=True)
        if target.stat().st_size>=MAX_BYTES: raise RuntimeError('Highlight exceeds size limit')
    payload={'clips':entries,'highlight':str(target),'best':str(best[0]),'worst':str(worst[0]),'highlight_order':['best: final up to 8 seconds','worst: final up to 8 seconds'],'max_bytes':MAX_BYTES}
    (output/'index.json').write_text(json.dumps(payload,indent=2)); return payload
