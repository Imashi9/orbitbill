import pytest

from orbitbill.credit_control import ChargingEngine, InsufficientBalance
from orbitbill.models import Product, UsageEvent


def engine(balance=1000):
    e = ChargingEngine()
    e.open_account("a1", balance)
    return e


def ev(i="e1", area=10, product=Product.SPOT):
    return UsageEvent(i, "a1", product, area)


def test_reserve_holds_funds_then_commit_debits():
    e = engine()
    e.reserve(ev())
    assert e.accounts["a1"].available == 880
    assert e.accounts["a1"].balance == 1000
    e.commit("e1")
    assert e.accounts["a1"].balance == 880
    assert e.accounts["a1"].reserved == 0


def test_insufficient_balance_rejected():
    with pytest.raises(InsufficientBalance):
        engine(50).reserve(ev())


def test_release_returns_funds():
    e = engine()
    e.reserve(ev())
    e.release("e1")
    assert e.accounts["a1"].available == 1000


def test_duplicate_event_billed_once():
    e = engine()
    assert e.charge(ev()) is not None
    assert e.charge(ev()) is None
    assert e.accounts["a1"].balance == 880


def test_release_restores_free_allowance():
    e = engine()
    e.reserve(ev("x", 100, Product.ARCHIVE))
    assert e.accounts["a1"].free_archive_left == 400
    e.release("x")
    assert e.accounts["a1"].free_archive_left == 500
