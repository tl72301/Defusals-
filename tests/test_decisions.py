import json
import time
import pytest
from defuse.decisions import Decisions, build_request, validate_endpoint
from defuse.engine import Bomb
from defuse.runner import shuffle_options, Clock, run_attempt


def query():
    b=Bomb(8); return b.view(),shuffle_options(b.legal(),8,0)[1]

def test_documented_body_and_no_answer_hint(stub,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','SENTINEL_SECRET_DO_NOT_SEND')
    view,options=query(); answer=Decisions(stub['url']).ask(view,options)
    assert answer.choice=='A' and answer.input_tokens==123 and answer.cost_usd==0 and not answer.error
    body=stub['requests'][0]
    assert body==build_request(view,options)
    assert body['model']=='gpt-6-luna' and len(body['questions'])==1
    assert body['input'][0]['role']=='user' and body['input'][0]['type']=='message'
    assert all(set(c)=={'value','description'} for c in body['questions'][0]['choices'])
    assert 'right_action' not in body['input'][0]['content'][0]['text']
    assert 'SENTINEL_SECRET_DO_NOT_SEND' not in json.dumps(stub)
    assert stub['headers'][0]['Authorization']=='Bearer local-test-no-credential'

@pytest.mark.parametrize('mode,error',[('refusal','refusal'),('invalid','invalid_answer')])
def test_refusal_invalid_no_retry(stub,mode,error):
    stub['mode']=mode; a=Decisions(stub['url']).ask(*query())
    assert a.error==error and a.input_tokens==123 and len(stub['requests'])==1

@pytest.mark.parametrize('endpoint',['https://evil.example/v1/decisions','http://api.openai.com/v1/decisions','http://127.0.0.1.evil.test/x',
    'file:///tmp/stub','http://user:password@localhost/x','http://localhost/x?key=x','http://192.168.1.1/x'])
def test_endpoint_overrides_are_only_loopback(endpoint):
    with pytest.raises(ValueError): validate_endpoint(endpoint)

def test_deadline_and_no_retry(stub):
    stub['delay']=.5
    start=time.monotonic(); a=Decisions(stub['url'],timeout=.1).ask(*query()); elapsed=time.monotonic()-start
    assert a.error=='timeout' and elapsed<.25
    time.sleep(.52)
    assert len(stub['requests'])==1

def test_http_failure_no_retry(stub):
    stub['status']=500; a=Decisions(stub['url']).ask(*query())
    assert a.error=='http_500' and len(stub['requests'])==1

def test_realtime_vs_paused_slow_stub(stub,tmp_path):
    stub['delay']=.15
    results={}
    for mode in ['realtime','paused']:
        folder,r=run_attempt(8,'decisions',mode,endpoint=stub['url'],seconds=5,output=tmp_path,video=False,max_requests=1,step_seconds=0)
        actions=[json.loads(x) for x in (folder/'actions.jsonl').read_text().splitlines()]
        row=actions[0]; results[mode]=row['game_after']-row['game_at']
        assert row['answer']['latency']>=.15
    assert results['realtime']>=.15
    assert results['paused']<.03

def test_expired_countdown_during_request_cannot_win(stub,tmp_path):
    stub['delay']=.15
    _,r=run_attempt(8,'decisions',seconds=.05,endpoint=stub['url'],output=tmp_path,video=False)
    assert not r['defused'] and r['end_reason']=='countdown' and r['actions']==1

def test_live_request_blocked_without_key_or_approval(monkeypatch,tmp_path):
    from defuse.budget import Budget, BudgetError
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValueError): Decisions(budget=Budget(tmp_path)).ask(*query())
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-a-real-key')
    with pytest.raises(BudgetError): Decisions(budget=Budget(tmp_path)).ask(*query())

def test_options_shuffle_reproducible_and_not_fixed_A():
    b=Bomb(20)
    a=shuffle_options(b.legal(),20,0)
    assert a==shuffle_options(b.legal(),20,0)
    orders={tuple(o['id'] for o in shuffle_options(b.legal(),20,i)[1]) for i in range(20)}
    assert len(orders)>5

def test_official_schema_allows_empty_distribution():
    from defuse.decisions import parse_response
    a=parse_response({'answers':[{'type':'choice','name':'action','choice':'A','confidence':.9,'probabilities':[]}]},['A','B'])
    assert a.choice=='A' and a.probabilities==[]


def test_live_accounting_with_mock_transport_and_key_redaction(monkeypatch,tmp_path):
    from defuse.budget import Budget
    import httpx
    key='PRIVATE_TEST_SENTINEL'
    monkeypatch.setenv('OPENAI_API_KEY',key)
    b=Budget(tmp_path); b.approve(1,confirm=True)
    calls=[]
    class FakeClient:
        def __init__(self,**kw):
            assert kw['follow_redirects'] is False and kw['trust_env'] is True
            assert kw['verify'].verify_mode==2
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,content,headers):
            calls.append(url)
            return httpx.Response(200,headers={'x-request-id':key},json={'answers':[{'type':'refusal','name':'action'}],'usage':{'input_tokens':456}})
    monkeypatch.setattr(httpx,'Client',FakeClient)
    answer=Decisions(budget=b).ask(*query())
    assert answer.error=='refusal' and answer.input_tokens==456 and answer.request_id is None
    assert b.show()['reported_tokens']==456 and b.show()['unresolved_requests']==0
    assert len(calls)==1
    for file in tmp_path.iterdir():
        if file.is_file(): assert key not in file.read_text()
    assert key not in json.dumps(answer.as_dict())


def test_timeout_retains_conservative_billing_reservation(monkeypatch,tmp_path):
    from defuse.budget import Budget
    import httpx
    monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    b=Budget(tmp_path); b.approve(1,confirm=True)
    class FakeClient:
        def __init__(self,**kw): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,*args,**kw): raise httpx.ReadTimeout('never log this message')
    monkeypatch.setattr(httpx,'Client',FakeClient)
    answer=Decisions(budget=b).ask(*query())
    assert answer.billing_unknown and answer.error=='timeout' and answer.input_tokens is None
    assert b.show()['requests']==1 and b.show()['unresolved_requests']==1
    assert float(b.show()['accounted_usd'])>0
