import pytest

from orbitbill.models import Product, UsageEvent
from orbitbill.rating import rate


def ev(product=Product.SPOT, area=10, res=1.0, rush=False):
    return UsageEvent("e1", "a1", product, area, res, rush)


def test_basic_rate():
    assert rate(ev())[0] == 120.0


def test_rush_and_fine_resolution_stack():
    charge, _, note = rate(ev(res=0.4, rush=True))
    assert charge == 120.0 * 1.5 * 2.0
    assert "rush" in note and "fine resolution" in note


def test_archive_free_allowance_consumed_first():
    charge, free, _ = rate(ev(Product.ARCHIVE, 600), free_left=500)
    assert free == 500 and charge == 100.0


def test_rush_does_not_apply_to_archive():
    assert rate(ev(Product.ARCHIVE, 10, rush=True))[0] == 10.0


def test_invalid_area():
    with pytest.raises(ValueError):
        rate(ev(area=0))
