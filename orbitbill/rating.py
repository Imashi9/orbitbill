from __future__ import annotations

from .models import Product, Tariff, UsageEvent

DEFAULT_TARIFF = Tariff(
    rate_per_km2={
        Product.SPOT: 12.0,
        Product.STRIP: 6.0,
        Product.SCAN: 2.5,
        Product.ARCHIVE: 1.0,
    },
    free_archive_km2=500.0,
)


def rate(event: UsageEvent, tariff: Tariff = DEFAULT_TARIFF,
         free_left: float = 0.0) -> tuple[float, float, str]:
    """Return (charge, free_km2_used, note) for one event.

    The free allowance only applies to archive downloads, and is consumed
    before any money is charged, like a free-unit bucket in an OCS.
    """
    if event.area_km2 <= 0:
        raise ValueError("area_km2 must be positive")

    free_used = 0.0
    billable = event.area_km2
    if event.product is Product.ARCHIVE and free_left > 0:
        free_used = min(free_left, event.area_km2)
        billable -= free_used

    price = billable * tariff.rate_per_km2[event.product]
    notes = [f"{event.product.value} {event.area_km2:g} km2"]
    if free_used:
        notes.append(f"{free_used:g} km2 free allowance")
    if event.resolution_m <= tariff.fine_resolution_threshold_m and event.product is not Product.ARCHIVE:
        price *= tariff.fine_resolution_multiplier
        notes.append(f"fine resolution x{tariff.fine_resolution_multiplier:g}")
    if event.rush and event.product is not Product.ARCHIVE:
        price *= tariff.rush_multiplier
        notes.append(f"rush x{tariff.rush_multiplier:g}")
    return round(price, 2), free_used, ", ".join(notes)
