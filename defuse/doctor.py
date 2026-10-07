"""Check offline readiness; live credentials and budget are optional unless --live."""
if __name__ == '__main__':
    from defuse._environment import bootstrap
    bootstrap('defuse.doctor')

import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from defuse.budget import Budget, DEFAULT_DIR

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--live',action='store_true'); p.add_argument('--budget-dir',type=Path,default=DEFAULT_DIR); args=p.parse_args(argv)
    missing=[]
    if sys.version_info<(3,11): missing.append('Python 3.11+')
    else: print('PASS Python',sys.version.split()[0])
    for package in ['PIL','numpy','httpx','imageio_ffmpeg']:
        try: importlib.import_module(package); print('PASS package',package)
        except ImportError: missing.append('package '+package+' (run bash scripts/setup.sh)')
    try:
        from defuse.engine import Bomb
        from defuse.render import ffmpeg_binary, frame
        exe=ffmpeg_binary(); subprocess.run([exe,'-version'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory(prefix='defuse-doctor-') as td:
            png=Path(td)/'frame.png'; mp4=Path(td)/'render.mp4'
            frame(Bomb(0).snapshot(),{'seed':0,'difficulty':'medium','controller':'solver','timing':'realtime'}).save(png)
            subprocess.run([exe,'-loglevel','error','-y','-loop','1','-i',str(png),'-t','0.1','-r','30','-c:v','libx264','-threads','2','-pix_fmt','yuv420p',str(mp4)],check=True,capture_output=True)
            subprocess.run([exe,'-loglevel','error','-i',str(mp4),'-f','null','-'],check=True,capture_output=True)
        print('PASS ffmpeg and 1280x720 H.264 render/decode')
    except Exception as e: missing.append('ffmpeg/Pillow render ('+type(e).__name__+')')
    key=bool(os.environ.get('OPENAI_API_KEY')); approval=Budget(args.budget_dir).show()
    print(('PRESENT' if key else 'MISSING (optional offline)'),'OPENAI_API_KEY; value never displayed')
    print('Budget:',json.dumps(approval))
    if args.live:
        if not key: missing.append('OPENAI_API_KEY via secure environment configuration')
        if not approval['approved']: missing.append('explicit budget approval with --confirm')
    if missing:
        for item in missing: print('MISSING',item)
        return 2
    print('PASS '+('live prerequisites (no request sent)' if args.live else 'offline development ready; no paid requests sent'))
    return 0

if __name__=='__main__': raise SystemExit(main())
