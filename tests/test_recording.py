import json
from pathlib import Path
import shutil
import subprocess
import pytest
from defuse.runner import run_attempt
from defuse.render import read_jsonl, ffmpeg_binary
from defuse.reports import report
from defuse.clips import clips, MAX_BYTES
from defuse.__main__ import main

@pytest.mark.media
def test_recording_report_clips_and_duplicate_seeds(tmp_path):
    folder,result=run_attempt(3,'first_option',seconds=5,output=tmp_path,step_seconds=.02)
    for name in ['manifest.json','actions.jsonl','api-usage.jsonl','results.json','gameplay.mp4']: assert (folder/name).exists()
    actions=read_jsonl(folder/'actions.jsonl')
    assert len(actions)==result['actions'] and sum(a['correct'] for a in actions)==result['correct_actions']
    assert abs(result['video']['duration']-result['wall_duration'])<=1/30
    assert result['cost_usd']==0 and result['requests']==0
    assert all(a['answer']['choice']=='A' for a in actions)
    ffprobe=shutil.which('ffprobe')
    if ffprobe:
        metadata=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(folder/'gameplay.mp4')]))
        stream=metadata['streams'][0]
        assert (stream['width'],stream['height'],stream['r_frame_rate'],stream['codec_name'])==(1280,720,'30/1','h264')
        assert abs(float(metadata['format']['duration'])-result['wall_duration'])<.04
    subprocess.run([ffmpeg_binary(),'-v','error','-i',str(folder/'gameplay.mp4'),'-f','null','-'],check=True,capture_output=True)
    run_attempt(3,'first_option',seconds=5,output=tmp_path,step_seconds=.02)
    payload=report(tmp_path)
    assert len(payload['duplicate_attempts_excluded'])==1 and payload['groups'][0]['attempts']==1
    assert payload['groups'][0]['first_option_fraction']==1
    review=clips(tmp_path)
    assert all(Path(x['path']).stat().st_size<MAX_BYTES for x in review['clips'])
    assert Path(review['highlight']).stat().st_size<MAX_BYTES


def test_smoke_and_batch_commands_use_stub(stub,tmp_path):
    smoke=tmp_path/'smoke'; batch=tmp_path/'batch'
    assert main(['smoke','--seed','12','--requests','2','--endpoint',stub['url'],'--no-video','--output',str(smoke),'--step-seconds','0'])==0
    r=json.loads(next(smoke.rglob('results.json')).read_text()); assert r['requests']==2 and r['cost_usd']==0 and r['stub']
    assert main(['batch','--seeds','12','13','--controllers','decisions','--timings','realtime','paused','--endpoint',stub['url'],
                 '--max-requests','1','--no-video','--step-seconds','0','--output',str(batch)])==0
    assert len(list(batch.rglob('results.json')))==4
    assert main(['batch','--seeds','12','12','--no-video','--output',str(batch)])==2
    assert main(['smoke','--seed','1','--requests','31','--endpoint',stub['url']])==2

@pytest.mark.media
def test_final_video_frame_uses_final_action_even_between_frame_boundaries(tmp_path,monkeypatch):
    import defuse.render as rendering
    folder,result=run_attempt(3,'first_option',output=tmp_path,video=False,step_seconds=0)
    actions=read_jsonl(folder/'actions.jsonl')
    observed=[]
    original=rendering.frame
    def capture(state,manifest,options=(),answer=None,correct=None,focus=None,wall=0,thinking=False):
        observed.append({'state':state,'options':options,'answer':answer,'focus':focus})
        return original(state,manifest,options,answer,correct,focus,wall,thinking)
    monkeypatch.setattr(rendering,'frame',capture)
    rendering.render_run(folder)
    assert observed[-1]['options']==actions[-1]['options']
    assert observed[-1]['answer']==actions[-1]['answer']
    assert observed[-1]['focus']==actions[-1]['module_id']
    assert observed[-1]['state']==result['final_state']


def test_cli_live_attempt_cannot_run_without_approval(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    assert main(['attempt','--seed','8','--controller','decisions','--no-video','--output',str(tmp_path)])==2
    folder=next(tmp_path.iterdir())
    result=json.loads((folder/'results.json').read_text())
    assert result['end_reason']=='budget_or_configuration_blocked'
    assert result['requests']==0 and result['cost_usd']==0
    assert (folder/'api-usage.jsonl').read_text()==''

@pytest.mark.media
def test_interrupt_is_visible_at_its_event_time_between_actions(tmp_path,monkeypatch):
    from copy import deepcopy
    from defuse.engine import Bomb
    import defuse.render as rendering
    bomb=Bomb(7,'hard'); initial=bomb.snapshot()
    module=next(m for m in initial['modules'] if m['kind']=='interrupt')
    interrupt_state={**module['state'],'active':True,'pressure':88,'deadline':10.5}
    final=deepcopy(initial)
    next(m for m in final['modules'] if m['kind']=='interrupt')['state']=interrupt_state
    manifest={'seed':7,'difficulty':'hard','controller':'solver','timing':'realtime','initial_state':initial,'limits':{'seconds':180}}
    result={'wall_duration':1.,'final_state':final}
    row={'request_at':0.,'decision_at':.01,'game_at':0.,'game_after':.01,'before':initial,'after':initial,'module_id':'labyrinth-1',
         'options':[],'answer':{'latency':.01,'choice':None},'correct':True}
    for name,value in [('manifest.json',manifest),('results.json',result)]: (tmp_path/name).write_text(json.dumps(value))
    (tmp_path/'actions.jsonl').write_text(json.dumps(row)+'\n')
    (tmp_path/'events.jsonl').write_text(json.dumps({'type':'interrupt','module':module['id'],'at':.5,'wall_at':1.,'state':interrupt_state,'strikes':0})+'\n')
    states=[]; original=rendering.frame
    def capture(state,manifest,options=(),answer=None,correct=None,focus=None,wall=0,thinking=False):
        states.append((wall,deepcopy(state)))
        return original(state,manifest,options,answer,correct,focus,wall,thinking)
    monkeypatch.setattr(rendering,'frame',capture)
    rendering.render_run(tmp_path)
    before=next(s for t,s in states if .3<=t<.5)
    after=next(s for t,s in states if .6<=t<.8)
    assert not next(m for m in before['modules'] if m['kind']=='interrupt')['state']['active']
    demand=next(m for m in after['modules'] if m['kind']=='interrupt')['state']
    assert demand['active'] and demand['pressure']==88
