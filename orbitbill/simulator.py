"""Synthetic usage generator. All data is simulated; nothing here comes from a real operator."""
from __future__ import annotations

import random

from .models import Product, UsageEvent

HOURS_PER_DAY = 24


def generate(account_id: str = "acme-maritime", days: int = 30, seed: int = 7,
             inject_spike_day: int | None = 21, duplicates: int = 3) -> list[UsageEvent]:
    rng = random.Random(seed)
    events: list[UsageEvent] = []
    n = 0

    def add(day: int, product: Product, area: float, res: float, rush: bool, hour: float):
        nonlocal n
        n += 1
        events.append(UsageEvent(f"evt-{n:05d}", account_id, product, round(area, 1), res,
                                 rush, day * HOURS_PER_DAY + hour))

    for day in range(days):
        for _ in range(rng.randint(2, 5)):
            product = rng.choices(list(Product), weights=[3, 3, 2, 5])[0]
            area = {Product.SPOT: rng.uniform(5, 25), Product.STRIP: rng.uniform(40, 120),
                    Product.SCAN: rng.uniform(200, 600), Product.ARCHIVE: rng.uniform(20, 150)}[product]
            res = rng.choice([0.25, 0.5, 1.0, 3.0])
            add(day, product, area, res, rng.random() < 0.1, rng.uniform(0, 23))

    if inject_spike_day is not None:
        # a runaway tasking script: dozens of rush fine-resolution spot requests in two hours
        for _ in range(40):
            add(inject_spike_day, Product.SPOT, rng.uniform(8, 20), 0.25, True, rng.uniform(2, 4))

    # retransmitted events: same event_id sent twice, must be billed once
    for dup in rng.sample(events, min(duplicates, len(events))):
        events.append(dup)

    events.sort(key=lambda e: e.timestamp)
    return events
