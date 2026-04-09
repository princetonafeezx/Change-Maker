"""TypedDict contracts for this package.

Runtime code uses plain dicts; these types are for documentation and static checks.
"""

from __future__ import annotations

from datetime import date
from typing import TypedDict

from typing_extensions import NotRequired


class CategorizedRecord(TypedDict):
    """Single transaction row when saving or loading categorized CSV data."""

    date: str | date
    merchant: str
    amount: float
    category: str
    subcategory: NotRequired[str]
    confidence: NotRequired[float]
    match_type: NotRequired[str]


class GreedyTraceStep(TypedDict):
    """One step in the optional greedy trace for :func:`change_maker.calculate_change`."""

    denomination: int
    name: str
    before: int
    count: int
    after: int


class ParsedAmountToCents(TypedDict):
    """Return value of :func:`change_maker.parse_amount_to_cents`."""

    input_text: str
    cents: int
    dollars: float
    rounded: bool


class ChangeResult(TypedDict):
    """Return value of :func:`change_maker.calculate_change`.

    Parsing errors raise :class:`ValueError` before a result is returned; every
    successful return includes all keys below.
    """

    ok: bool
    cents: int
    amount: float
    rounded: bool
    breakdown: dict[int, int]
    trace: list[GreedyTraceStep]
    bill_count: int
    coin_count: int
    verification: float
    used_denominations: set[int]
    unused_denominations: set[int]
    message: str
