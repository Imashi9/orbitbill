"""Online credit control: reserve -> commit / release.

Mirrors the Diameter Gy / OCS pattern: the cost of a request is reserved
against the balance *before* the service is delivered, then committed with
the final usage, or released if the request fails.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Account, LedgerEntry, Tariff, UsageEvent
from .rating import DEFAULT_TARIFF, rate


class InsufficientBalance(Exception):
    pass


@dataclass
class Reservation:
    event: UsageEvent
    amount: float
    free_km2: float


class ChargingEngine:
    def __init__(self, tariff: Tariff = DEFAULT_TARIFF):
        self.tariff = tariff
        self.accounts: dict[str, Account] = {}
        self._reservations: dict[str, Reservation] = {}
        self._seen: set[str] = set()

    def open_account(self, account_id: str, balance: float) -> Account:
        acct = Account(account_id, balance, self.tariff.free_archive_km2)
        self.accounts[account_id] = acct
        return acct

    def reserve(self, event: UsageEvent) -> Reservation:
        if event.event_id in self._reservations:
            return self._reservations[event.event_id]  # idempotent retry
        acct = self.accounts[event.account_id]
        amount, free_used, _ = rate(event, self.tariff, acct.free_archive_left)
        if amount > acct.available:
            raise InsufficientBalance(
                f"need {amount:.2f}, available {acct.available:.2f}")
        acct.reserved += amount
        acct.free_archive_left -= free_used
        res = Reservation(event, amount, free_used)
        self._reservations[event.event_id] = res
        return res

    def commit(self, event_id: str) -> LedgerEntry:
        res = self._reservations.pop(event_id)
        acct = self.accounts[res.event.account_id]
        acct.reserved -= res.amount
        acct.balance = round(acct.balance - res.amount, 2)
        _, _, note = rate(res.event, self.tariff, res.free_km2)
        entry = LedgerEntry(event_id, acct.account_id, res.event.product,
                            res.event.area_km2, res.amount, res.free_km2,
                            note, res.event.timestamp)
        acct.ledger.append(entry)
        self._seen.add(event_id)
        return entry

    def release(self, event_id: str) -> None:
        res = self._reservations.pop(event_id, None)
        if res:
            acct = self.accounts[res.event.account_id]
            acct.reserved -= res.amount
            acct.free_archive_left += res.free_km2

    def charge(self, event: UsageEvent) -> LedgerEntry | None:
        """One-shot reserve+commit. Returns None for an already-billed event."""
        if event.event_id in self._seen:
            return None
        self.reserve(event)
        return self.commit(event.event_id)
