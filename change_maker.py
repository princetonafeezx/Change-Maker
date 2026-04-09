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

def parse_amount_to_cents(amount_text: str) -> ParsedAmountToCents:

    original = (amount_text or "").strip()
    if not original:
        raise ValueError("Please enter an amount.")

    had_dollar_symbol = "$" in original
    cleaned = original.replace("$", "").replace(",", "").strip()

    if cleaned.startswith("+"):
        cleaned = cleaned[1:].strip()
    if cleaned.startswith("-"):
        raise ValueError("Negative amounts are not allowed for change making.")
    if not cleaned:
        raise ValueError("Please enter an amount.")
    if "e" in cleaned.lower():
        raise ValueError(
            "Scientific notation is not supported. Use a plain amount like 14.73 or $14.73."
        )
