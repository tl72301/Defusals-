from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
import stat
import pytest
from defuse.budget import Budget, BudgetError, main


def test_explicit_approval_required(tmp_path):
    b=Budget(tmp_path/'private')
    with pytest.raises(BudgetError): b.reserve(100)
    with pytest.raises(BudgetError): b.approve(1,confirm=False)
    assert not b.show()['approved']
    assert main(['--directory',str(b.path),'approve','--total-usd','1'])==2


def test_ledger_cost_caps_and_revoke(tmp_path):
    b=Budget(tmp_path/'private'); b.approve('.00002',smoke_requests=1,attempt_requests=2,confirm=True)
    rid=b.reserve(100,'smoke'); b.settle(rid,70,'stub-id')
    assert Decimal(b.show()['accounted_usd'])==Decimal('.000007')
    assert b.show()['reported_tokens']==70
    with pytest.raises(BudgetError): b.reserve(1,'smoke')
    with pytest.raises(BudgetError): b.reserve(1,batch=True)
    with pytest.raises(BudgetError): b.reserve(131)
    pending=b.reserve(100)
    assert b.show()['unresolved_requests']==1
    with pytest.raises(BudgetError): b.reserve(31)
    b.revoke()
    with pytest.raises(BudgetError): b.reserve(1)
    assert stat.S_IMODE(b.path.stat().st_mode)==0o700
    for name in ['approval.json','ledger.jsonl','lock']: assert stat.S_IMODE((b.path/name).stat().st_mode)==0o600


def test_caps_concurrent_reservations_and_crash_retention(tmp_path):
    b=Budget(tmp_path); b.approve(1,attempt_requests=3,confirm=True)
    def reserve(_):
        try: return b.reserve(100)
        except BudgetError: return None
    with ThreadPoolExecutor(max_workers=8) as pool: outcomes=list(pool.map(reserve,range(12)))
    assert sum(x is not None for x in outcomes)==3
    assert Budget(tmp_path).show()['unresolved_requests']==3


def test_smoke_hard_cap_and_estimate_violation(tmp_path):
    b=Budget(tmp_path)
    with pytest.raises(BudgetError): b.approve(1,smoke_requests=31,confirm=True)
    b.approve(1,confirm=True)
    rid=b.reserve(10)
    with pytest.raises(BudgetError): b.settle(rid,11)
    assert not b.show()['approved']
    assert b.show()['reported_tokens']==11
    with pytest.raises(BudgetError): b.settle(rid,11)


def test_new_approval_preserves_old_ledger(tmp_path):
    b=Budget(tmp_path); b.approve(1,confirm=True); b.reserve(100)
    previous=(tmp_path/'ledger.jsonl').read_text(); b.approve(2,confirm=True)
    assert (tmp_path/'ledger.jsonl').read_text()==previous
    assert b.show()['requests']==0
