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
    try:
        if "." in cleaned:
            decimal_amount = Decimal(cleaned)
            rounded = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cents = int(rounded * 100)
            rounded_happened = decimal_amount != rounded
            dollars = float(rounded)
        elif cleaned.isdigit():
            if had_dollar_symbol or len(cleaned) <= 2:
                decimal_amount = Decimal(cleaned)
                rounded = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                cents = int(rounded * 100)
                rounded_happened = False
                dollars = float(rounded)
            else:
                cents = int(cleaned)
                rounded_happened = False
                dollars = cents / 100
        else:
            raise ValueError
    except (InvalidOperation, ValueError):
        raise ValueError("That amount was not numeric. Try formats like 14.73, $14.73, or 1473.") from None

    return cast(
        ParsedAmountToCents,
        {
            "input_text": original,
            "cents": cents,
            "dollars": dollars,
            "rounded": rounded_happened,
        },
    )

def calculate_change(amount_text: str, verbose: bool = False) -> ChangeResult:
    parsed = parse_amount_to_cents(amount_text)
    cents = parsed["cents"]


    if cents == 0:
        return cast(
            ChangeResult,
            {
                "ok": True,
                "cents": 0,
                "amount": 0.0,
                "rounded": parsed["rounded"],
                "breakdown": {},
                "trace": [],
                "bill_count": 0,
                "coin_count": 0,
                "verification": 0.0,
                "used_denominations": set[int](),
                "unused_denominations": set(DENOMINATIONS.keys()),
                "message": "Zero dollars means there is no change to hand back.",
            },
        )

    remaining = cents
    breakdown: dict[int, int] = {}
    trace: list[GreedyTraceStep] = []
    used_denominations: set[int] = set()
    
    for value in sorted(DENOMINATIONS, reverse=True):
        info = DENOMINATIONS[value]
        count = remaining // value
        leftover = remaining % value
        if count:
            breakdown[value] = count
            used_denominations.add(value)
        if verbose:
            trace.append(
                cast(
                    GreedyTraceStep,
                    {
                        "denomination": value,
                        "name": info["name"],
                        "before": remaining,
                        "count": int(count),
                        "after": int(leftover),
                    },
                )
            )
        remaining = leftover
    
    unused_denominations = set(DENOMINATIONS.keys()) - used_denominations
    bill_count = 0
    coin_count = 0
    verification_cents = 0

    for value, count in breakdown.items():
        verification_cents += value * count
        if DENOMINATIONS[value]["type"] == "bill":
            bill_count += count
        else:
            coin_count += count

    return cast(
        ChangeResult,
        {
            "ok": True,
            "cents": cents,
            "amount": parsed["dollars"],
            "rounded": parsed["rounded"],
            "breakdown": breakdown,
            "trace": trace,
            "bill_count": bill_count,
            "coin_count": coin_count,
            "verification": verification_cents / 100,
            "used_denominations": used_denominations,
            "unused_denominations": unused_denominations,
            "message": "",
        },
    )

def print_denomination_info() -> None:
    print("Supported denominations")
    print("-" * 40)
    for value in sorted(DENOMINATIONS, reverse=True):
        info = DENOMINATIONS[value]
        display_value = format_money(value / 100)
        print(f"{display_value:<10}{info['name']:<14}{info['type']}")
