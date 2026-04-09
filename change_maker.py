from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import cast

from schemas import ChangeResult, GreedyTraceStep, ParsedAmountToCents
from storage import format_money

DENOMINATIONS: dict[int, dict[str, str]] = {
    10000: {"name": "$100 bill", "type": "bill"},
    5000: {"name": "$50 bill", "type": "bill"},
    2000: {"name": "$20 bill", "type": "bill"},
    1000: {"name": "$10 bill", "type": "bill"},
    500: {"name": "$5 bill", "type": "bill"},
    100: {"name": "$1 bill", "type": "bill"},
    25: {"name": "quarter", "type": "coin"},
    10: {"name": "dime", "type": "coin"},
    5: {"name": "nickel", "type": "coin"},
    1: {"name": "penny", "type": "coin"},
}
