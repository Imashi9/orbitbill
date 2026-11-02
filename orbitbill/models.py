from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Product(str, Enum):
    SPOT = "spot"          # high-resolution single scene
    STRIP = "strip"        # long strip acquisition
    SCAN = "scan"          # wide-area scan
    ARCHIVE = "archive"    # download of previously captured imagery


@dataclass(frozen=True)
class UsageEvent:
    """One chargeable usage event (a 'CDR' in telecom terms)."""
    event_id: str
    account_id: str
    product: Product
    area_km2: float
    resolution_m: float = 1.0
    rush: bool = False
    timestamp: float = 0.0


@dataclass
class Tariff:
    """Price per km2 by product, plus modifiers."""
    rate_per_km2: dict[Product, float]
    rush_multiplier: float = 2.0
    fine_resolution_threshold_m: float = 0.5
    fine_resolution_multiplier: float = 1.5
    free_archive_km2: float = 0.0   # monthly free allowance bucket


@dataclass
class LedgerEntry:
    event_id: str
    account_id: str
    product: Product
    area_km2: float
    charged: float
    free_km2_used: float
    note: str
    timestamp: float = 0.0


@dataclass
class Account:
    account_id: str
    balance: float
    free_archive_left: float = 0.0
    reserved: float = 0.0
    ledger: list[LedgerEntry] = field(default_factory=list)

    @property
    def available(self) -> float:
        return round(self.balance - self.reserved, 2)
