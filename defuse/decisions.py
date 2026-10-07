"""One text choice per request. No retries, redirects, or remote endpoint overrides."""
from dataclasses import dataclass, asdict
import ipaddress
import json
import math
import os
import queue
import ssl
import threading
import time
from urllib.parse import urlsplit
import httpx
from defuse.budget import Budget, BudgetError, token_cost

API_URL='https://api.openai.com/v1/decisions'
MODEL='gpt-6-luna'

@dataclass
class Answer:
    choice: str | None = None
    confidence: float | None = None
    probabilities: list | None = None
    latency: float = 0.0
    input_tokens: int | None = None
    cost_usd: float = 0.0
    request_id: str | None = None
    error: str | None = None
    reservation_id: str | None = None
    billing_unknown: bool = False
    def as_dict(self): return asdict(self)

def validate_endpoint(endpoint):
    if endpoint==API_URL: return False
    u=urlsplit(endpoint)
    try: loopback=ipaddress.ip_address(u.hostname or '').is_loopback
    except ValueError: loopback=u.hostname=='localhost'
    if not loopback or u.scheme not in ('http','https') or u.username or u.password or u.query or u.fragment:
        raise ValueError('Endpoint overrides must be loopback HTTP(S) URLs without credentials, query, or fragment')
    return True

MAX_QUESTIONS=200

def build_many(view,questions):
    """One shared text and several named choice questions: [(name, instructions, options), ...]."""
    if not 1<=len(questions)<=MAX_QUESTIONS: raise ValueError(f'1..{MAX_QUESTIONS} questions per request')
    names=[q[0] for q in questions]
    if len(set(names))!=len(names): raise ValueError('question names must be unique')
    if any(not 2<=len(q[2])<=8 for q in questions): raise ValueError('Each decision needs 2..8 options')
    return {'model':MODEL,'input':[{'role':'user','type':'message','content':[{'type':'input_text','text':view}]}],
            'questions':[{'type':'choice','name':n,'instructions':i,'choices':[{'value':o['value'],'description':o['description']} for o in opts]}
                         for n,i,opts in questions]}

def build_request(view,options,instructions=None):
    if not 2<=len(options)<=8: raise ValueError('Each decision needs 2..8 options')
    text=view if isinstance(view,str) else json.dumps(view,sort_keys=True,ensure_ascii=False)
    return {'model':MODEL,'input':[{'role':'user','type':'message','content':[{'type':'input_text','text':text}]}],
            'questions':[{'type':'choice','name':'action','instructions':instructions or 'Apply the supplied manual to the visible state. Choose one literal action to perform now.',
                          'choices':[{'value':o['value'],'description':o['description']} for o in options]}]}

def parse_response(data,allowed):
    if not isinstance(data,dict): raise ValueError('response is not an object')
    answers=data.get('answers')
    if not isinstance(answers,list) or len(answers)!=1: raise ValueError('expected one answer')
    a=answers[0]
    if not isinstance(a,dict): raise ValueError('answer is not an object')
    if a.get('name')!='action': raise ValueError('wrong question name')
    return parse_answer(a,allowed)

def parse_answer(a,allowed):
    if not isinstance(a,dict): raise ValueError('answer is not an object')
    if a['type']=='refusal': return Answer(error='refusal')
    if a['type']!='choice' or a['choice'] not in allowed: raise ValueError('invalid choice')
    c=a['confidence']; probs=a['probabilities']
    if isinstance(c,bool) or not isinstance(c,(float,int)) or not math.isfinite(c) or not 0<=c<=1: raise ValueError('invalid confidence')
    if not isinstance(probs,list): raise ValueError('invalid probabilities')
    if not all(isinstance(p,dict) for p in probs): raise ValueError('invalid probability entry')
    labels=[p.get('value') for p in probs]
    if any(x not in allowed for x in labels) or len(set(labels))!=len(labels): raise ValueError('invalid probability labels')
    values=[p.get('probability') for p in probs]
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=1 for x in values) or sum(values)>1.02:
        raise ValueError('invalid probability values')
    return Answer(choice=a['choice'],confidence=c,probabilities=probs)

class Decisions:
    def __init__(self,endpoint=API_URL,timeout=0.6,budget=None,category='attempt',batch=False):
        self.stub=validate_endpoint(endpoint)
        if not math.isfinite(timeout) or timeout<=0: raise ValueError('positive finite timeout required')
        self.endpoint,self.timeout,self.budget,self.category,self.batch=endpoint,timeout,budget or Budget(),category,batch
    def ask(self,view,options,instructions=None):
        answer,data=self._exchange(build_request(view,options,instructions))
        if data is None: return answer
        try:
            parsed=parse_response(data,[o['value'] for o in options])
            answer.choice,answer.confidence,answer.probabilities,answer.error=parsed.choice,parsed.confidence,parsed.probabilities,parsed.error
        except (KeyError,ValueError,TypeError,AttributeError): answer.error='invalid_answer'; answer.request_id=None
        return answer

    def ask_many(self,view,questions):
        """Several named questions in one request. Returns (shared Answer with latency/usage/error, {name: Answer})."""
        shared,data=self._exchange(build_many(view,questions))
        out={}
        if data is None: return shared,out
        answers=data.get('answers') if isinstance(data,dict) else None
        by_name={a.get('name'):a for a in answers if isinstance(a,dict)} if isinstance(answers,list) else {}
        for name,_,opts in questions:
            a=Answer(latency=shared.latency)
            try:
                parsed=parse_answer(by_name[name],[o['value'] for o in opts])
                a.choice,a.confidence,a.probabilities,a.error=parsed.choice,parsed.confidence,parsed.probabilities,parsed.error
            except (KeyError,ValueError,TypeError,AttributeError): a.error='invalid_answer'
            out[name]=a
        return shared,out

    def _exchange(self,body):
        """Send one request under the budget. Returns (Answer with latency/usage/error, response data or None)."""
        encoded=json.dumps(body,ensure_ascii=False).encode('utf8')
        key='local-test-no-credential' if self.stub else os.environ.get('OPENAI_API_KEY')
        if not key: raise ValueError('OPENAI_API_KEY is missing; add it securely before live runs')
        # Text token count cannot exceed UTF-8 bytes under byte tokenization. Extra overhead is deliberately generous.
        estimate=len(encoded)+8192
        reservation=None if self.stub else self.budget.reserve(estimate,self.category,self.batch)
        started=time.monotonic(); output=queue.Queue(maxsize=1)
        def send_once():
            try:
                ca=os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
                context=ssl.create_default_context(cafile=ca)
                with httpx.Client(verify=context,trust_env=not self.stub,follow_redirects=False,timeout=self.timeout) as client:
                    response=client.post(self.endpoint,content=encoded,headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
                    if response.status_code!=200:
                        output.put(('error','http_'+str(response.status_code))); return
                    # Never log arbitrary response/error text, which could reflect credentials.
                    output.put(('ok',response.json(),response.headers.get('x-request-id')))
            except httpx.TimeoutException: output.put(('error','timeout'))
            except Exception: output.put(('error','transport_or_json_error'))
        thread=threading.Thread(target=send_once,daemon=True); thread.start()
        try: result=output.get(timeout=max(.000001,self.timeout-(time.monotonic()-started)))
        except queue.Empty: result=('error','timeout')
        latency=time.monotonic()-started
        answer=Answer(latency=latency,reservation_id=reservation,billing_unknown=not self.stub)
        if result[0]=='error': answer.error=result[1]; return answer,None
        data,request_id=result[1:]
        request_id=request_id if request_id and key not in request_id else None
        # Usage is accounted even for a refusal or malformed answer.
        try:
            tokens=data['usage']['input_tokens']
            if isinstance(tokens,bool) or not isinstance(tokens,int) or tokens<0: raise ValueError()
            answer.input_tokens=tokens; answer.cost_usd=0.0 if self.stub else float(token_cost(tokens))
            answer.billing_unknown=False
            if reservation: self.budget.settle(reservation,tokens,request_id)
        except BudgetError:
            answer.error='budget_estimate_exceeded'; return answer,None
        except (KeyError,TypeError,ValueError):
            answer.error='invalid_usage'; return answer,None
        # IDs are opaque metadata; disallow an API key reflected as an ID.
        answer.request_id=request_id
        return answer,data
