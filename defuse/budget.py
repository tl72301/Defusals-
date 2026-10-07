"""Private, process-safe reservations. Unknown billing retains its full reservation."""
import argparse
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import fcntl
import json
import os
from pathlib import Path
import time
import uuid

PRICE = Decimal('0.0000001')  # USD per input token, operator-supplied experiment price
DEFAULT_DIR = Path('data/private/budget')

class BudgetError(RuntimeError): pass

def token_cost(tokens): return Decimal(tokens) * PRICE

def append_json(path, row):
    with open(path,'a',encoding='utf8') as f:
        f.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n'); f.flush(); os.fsync(f.fileno())

class Budget:
    def __init__(self, directory=DEFAULT_DIR): self.path = Path(directory)
    @contextmanager
    def locked(self):
        self.path.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(self.path,0o700)
        fd=os.open(self.path/'lock',os.O_CREAT|os.O_RDWR,0o600)
        with os.fdopen(fd,'a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            yield
    def _read(self):
        p=self.path/'approval.json'
        approval=json.loads(p.read_text()) if p.exists() else None
        ledger=self.path/'ledger.jsonl'
        rows=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
        return approval, rows
    def _write_approval(self,a):
        p=self.path/'approval.tmp'
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:
            json.dump(a,f,allow_nan=False); f.flush(); os.fsync(f.fileno())
        os.replace(p,self.path/'approval.json')
    def _append(self,row):
        path=self.path/'ledger.jsonl'
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        with os.fdopen(fd,'a') as f:
            f.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n'); f.flush(); os.fsync(f.fileno())
    def approve(self,total_usd,smoke_requests=30,attempt_requests=300,allow_batch=False,confirm=False):
        if not confirm: raise BudgetError('Nothing approved: --confirm is required')
        total=Decimal(str(total_usd))
        if not total.is_finite() or total<=0: raise BudgetError('total USD must be positive and finite')
        if not 0<=smoke_requests<=30 or attempt_requests<0: raise BudgetError('smoke cap must be 0..30; attempt cap must be nonnegative')
        with self.locked():
            old, rows=self._read()
            # A new explicit approval is a new allocation. Preserve all prior ledger entries.
            a={'id':uuid.uuid4().hex,'total_usd':str(total),'smoke_requests':smoke_requests,
               'attempt_requests':attempt_requests,'allow_batch':allow_batch,'active':True,'created_at':time.time()}
            self._write_approval(a)
        return self.show()
    @staticmethod
    def _usage(a,rows):
        reservations={r['id']:r for r in rows if r['event']=='reserve' and r['approval_id']==a['id']}
        settlements={r['id']:r for r in rows if r['event']=='settle' and r['id'] in reservations}
        cost=sum((Decimal(settlements[k]['cost_usd']) if k in settlements else Decimal(r['reserved_usd']) for k,r in reservations.items()),Decimal(0))
        return reservations, settlements, cost
    def show(self):
        with self.locked():
            a,rows=self._read()
            if not a: return {'approved':False,'message':'No paid requests authorized'}
            rs,ss,cost=self._usage(a,rows)
            return {'approved':a['active'],'approval':a,'accounted_usd':str(cost),
                    'remaining_usd':str(max(Decimal(0),Decimal(a['total_usd'])-cost)),
                    'requests':len(rs),'unresolved_requests':len(rs)-len(ss),
                    'reported_tokens':sum(s['input_tokens'] for s in ss.values())}
    def revoke(self):
        with self.locked():
            a,_=self._read()
            if a: a['active']=False; self._write_approval(a)
    def reserve(self,estimated_tokens,category='attempt',batch=False):
        if category not in ('smoke','attempt') or estimated_tokens<1: raise BudgetError('invalid reservation')
        with self.locked():
            a,rows=self._read()
            if not a or not a['active']: raise BudgetError('Paid requests require budget approve --confirm')
            rs,_,used=self._usage(a,rows)
            if batch and not a['allow_batch']: raise BudgetError('Batch requires an approval with --allow-batch')
            if sum(r['category']==category for r in rs.values())>=a[category+'_requests']: raise BudgetError(category+' request cap exhausted')
            amount=token_cost(estimated_tokens)
            if used+amount>Decimal(a['total_usd']): raise BudgetError('Estimated request cost exceeds remaining budget')
            rid=uuid.uuid4().hex
            self._append({'event':'reserve','id':rid,'approval_id':a['id'],'category':category,'estimated_tokens':estimated_tokens,'reserved_usd':str(amount),'at':time.time()})
            return rid
    def settle(self,rid,input_tokens,request_id=None):
        if not isinstance(input_tokens,int) or isinstance(input_tokens,bool) or input_tokens<0: raise BudgetError('invalid usage')
        with self.locked():
            a,rows=self._read()
            r=next((r for r in rows if r['event']=='reserve' and r['id']==rid),None)
            if r is None or any(x['event']=='settle' and x['id']==rid for x in rows): raise BudgetError('unknown or already settled reservation')
            self._append({'event':'settle','id':rid,'approval_id':r['approval_id'],'input_tokens':input_tokens,'cost_usd':str(token_cost(input_tokens)),'request_id':request_id,'at':time.time()})
            if input_tokens>r['estimated_tokens'] and a and a['id']==r['approval_id']:
                a['active']=False; self._write_approval(a)
                raise BudgetError('Usage exceeded conservative estimate; approval revoked')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--directory',type=Path,default=DEFAULT_DIR)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('approve'); a.add_argument('--total-usd',required=True); a.add_argument('--smoke-requests',type=int,default=30)
    a.add_argument('--attempt-requests',type=int,default=300); a.add_argument('--allow-batch',action='store_true'); a.add_argument('--confirm',action='store_true')
    sub.add_parser('show'); sub.add_parser('revoke'); args=p.parse_args(argv); b=Budget(args.directory)
    try:
        if args.command=='approve': result=b.approve(args.total_usd,args.smoke_requests,args.attempt_requests,args.allow_batch,args.confirm)
        elif args.command=='revoke': b.revoke(); result=b.show()
        else: result=b.show()
        print(json.dumps(result,indent=2)); return 0
    except (BudgetError,InvalidOperation) as e: print(str(e)); return 2

if __name__=='__main__': raise SystemExit(main())
