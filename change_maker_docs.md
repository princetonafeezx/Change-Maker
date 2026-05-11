# Architecture Decision Record
## App 09 — Change Maker
**Ledger Logic Group | Document 1 of 5**
**Status: Accepted**

---

## Context

The Change Maker is the ninth app in the portfolio and the second in the Ledger Logic group. It solves a classical cash-handling problem: given a dollar amount, produce the fewest bills and coins needed to make exact change. It is the first Ledger Logic app to work with integer cents internally, making it the natural place to introduce Decimal-based rounding and greedy algorithm reasoning in the portfolio.

---

## Decisions

### Decision 1 — Integer cents as the internal representation

**Chosen:** All arithmetic runs on integer cents. `parse_amount_to_cents()` converts input to cents before the greedy algorithm runs. The verification step converts back to dollars: `verification_cents / 100`.

**Rejected:** Float dollars throughout.

**Reason:** Float arithmetic on currency values produces rounding errors. `14.73 / 0.25` in floating point does not produce the integer `58.92` — it produces `58.919999...`. Integer cents eliminate this class of error entirely. The greedy algorithm is purely integer division and modulo, which are exact operations. This is the foundational lesson of the module: financial math should use integers or Decimal, never float division.

---

### Decision 2 — `Decimal` with `ROUND_HALF_UP` for input parsing

**Chosen:** `parse_amount_to_cents()` converts the input string to `Decimal`, quantizes to `Decimal("0.01")` with `ROUND_HALF_UP`, then multiplies by 100 and converts to `int`.

**Rejected:** Using `round(float(input), 2)` then multiplying by 100.

**Reason:** `round(float("14.735"), 2)` produces `14.73` in Python (banker's rounding). The module uses `ROUND_HALF_UP` to match the behavior a cashier expects — $14.735 rounds to $14.74. The `rounded` flag in `ParsedAmountToCents` surfaces when rounding occurred so the caller can notify the user.

---

### Decision 3 — Three input interpretation modes for digit-only strings

**Chosen:** Digit-only input is interpreted as: (a) dollars if `$` was present or string length ≤ 2 (`"14"` → $14.00), (b) raw cents if no `$` and length > 2 (`"1473"` → $14.73).

**Rejected:** Always treating digit-only strings as dollars.

**Reason:** Point-of-sale systems and cash registers frequently enter amounts as raw cents (`1473` for $14.73) without a decimal point or dollar sign. Supporting this convention makes the module usable in POS-adjacent contexts. The `had_dollar_symbol` flag disambiguates the intent when a `$` is present.

---

### Decision 4 — `DENOMINATIONS` dict as the sole source of truth

**Chosen:** `DENOMINATIONS: dict[int, dict[str, str]]` maps integer cent values to `{"name": ..., "type": "bill" | "coin"}`. The greedy loop, verification, bill/coin counting, and print functions all read from this dict. Adding a denomination requires only one dict entry.

**Rejected:** Hardcoding denomination values inside the greedy function.

**Reason:** The denomination set and the algorithm are orthogonal concerns. The algorithm works for any denomination set; the dict encodes which specific set this module uses. `print_denomination_info()` lists all supported denominations by iterating the same dict — it cannot go out of sync with the algorithm.

---

### Decision 5 — `verbose` flag for greedy trace

**Chosen:** When `verbose=True`, `calculate_change()` records a `GreedyTraceStep` for every denomination in the sorted order, including denominations with a count of zero. `print_change_result()` renders the trace as a step-by-step table.

**Rejected:** Always logging the trace, or never logging it.

**Reason:** The trace is the educational output that makes this module valuable beyond its functional use. Showing each denomination's `before` and `after` cents illustrates exactly how the greedy algorithm works. Making it optional via a flag means production use (no trace) and learning use (full trace) are both served by the same function.

---

### Decision 6 — Scientific notation rejection

**Chosen:** Both `parse_amount_to_cents()` and `parsing.parse_amount()` explicitly check for `"e"` in the cleaned string and raise `ValueError` with a plain-format suggestion.

**Rejected:** Allowing `1e2` as a valid input.

**Reason:** Scientific notation is a valid Python numeric literal but not a valid cash register input format. `Decimal("1e2")` would parse to `$100.00`, but `"1e2"` typed by a user likely means they made a keyboard error. Rejecting it with a clear message is the correct defensive behavior. Consistency between `parse_amount_to_cents()` and `parsing.parse_amount()` ensures the same rule applies across all Ledger Logic amount inputs.

---

## Consequences

**Positive:**
- Integer-cents algorithm produces exact results with no floating-point drift.
- `Decimal` + `ROUND_HALF_UP` matches cashier expectations.
- Greedy trace makes the algorithm's behavior transparent and educational.
- `DENOMINATIONS` dict is the single source of truth — algorithm and display stay in sync.
- Verification step (`verification_cents / 100 == original_amount`) provides a built-in correctness check.

**Negative / Trade-offs:**
- The greedy algorithm is optimal for the standard US denomination set (where each denomination is a multiple of smaller ones) but is not optimal for arbitrary denomination sets. For a set like `{1, 3, 4}`, the greedy algorithm would give 3 coins for `6` (`4+1+1`) while the optimal is 2 (`3+3`). This limitation is documented in the module docstring.
- The module covers only US cash denominations (no half-dollar or dollar coin). International currencies or unusual denomination sets require code changes to `DENOMINATIONS`.
- The three-mode digit-only parsing is a UX convenience that adds conditional logic. A user who enters `"100"` intending $1.00 will get $100.00. The length-based disambiguation is documented but not obvious.

---

*Constitution reference: Articles 1, 2, 3. Amendment 1.3: `parsing.py`, `schemas.py`, `storage.py` are pinned snapshots.*


---


# Technical Design Document
## App 09 — Change Maker
**Ledger Logic Group | Document 2 of 5**

---

## Overview

Change Maker parses a dollar amount, converts it to integer cents, and applies the greedy algorithm to produce the minimal bill/coin breakdown using standard US denominations. It optionally records a step-by-step trace of the algorithm.

**File:** `change_maker.py` (236 lines)
**Shared (pinned snapshots):** `parsing.py`, `schemas.py`, `storage.py`
**Entry point:** `main()` → `menu()`
**Dependencies:** `decimal` (stdlib); `schemas`, `storage` (Ledger Logic shared)

---

## Data Flow

```
Input: amount_text (str)
        │
        ▼
parse_amount_to_cents(amount_text)
        ├─ Strip: $, ,, whitespace, +
        ├─ Reject: empty, negative, scientific notation
        ├─ had_dollar_symbol → disambiguation flag
        ├─ "." in cleaned → Decimal → ROUND_HALF_UP → × 100 → int cents
        ├─ isdigit() + ($ or len ≤ 2) → treat as dollars
        ├─ isdigit() + no $ + len > 2  → treat as raw cents
        └─ else → ValueError
        │
        ▼
ParsedAmountToCents {input_text, cents, dollars, rounded}
        │
        ▼
calculate_change(amount_text, verbose)
        │
        ├─ cents == 0 → early return with zero-change message
        │
        └─ Greedy loop: sorted(DENOMINATIONS, reverse=True)
               ├─ count = remaining // denomination_value
               ├─ leftover = remaining % denomination_value
               ├─ if count → breakdown[value] = count
               ├─ if verbose → trace.append(GreedyTraceStep)
               └─ remaining = leftover
        │
        ▼
Post-loop:
        ├─ unused_denominations = all_keys - used_denominations
        ├─ bill_count, coin_count, verification_cents from breakdown
        └─ verification_cents / 100 == parsed["dollars"]  (correctness check)
        │
        ▼
ChangeResult {ok, cents, amount, rounded, breakdown, trace,
              bill_count, coin_count, verification,
              used_denominations, unused_denominations, message}
```

---

## Module-Level Constants

### `DENOMINATIONS`

```python
{
    10000: {"name": "$100 bill", "type": "bill"},
    5000:  {"name": "$50 bill",  "type": "bill"},
    2000:  {"name": "$20 bill",  "type": "bill"},
    1000:  {"name": "$10 bill",  "type": "bill"},
    500:   {"name": "$5 bill",   "type": "bill"},
    100:   {"name": "$1 bill",   "type": "bill"},
    25:    {"name": "quarter",   "type": "coin"},
    10:    {"name": "dime",      "type": "coin"},
    5:     {"name": "nickel",    "type": "coin"},
    1:     {"name": "penny",     "type": "coin"},
}
```

Keys are integer cent values. The greedy algorithm iterates `sorted(DENOMINATIONS, reverse=True)` — descending from $100 to $0.01.

---

## Function Reference

### `parse_amount_to_cents(amount_text: str) -> ParsedAmountToCents`

Full cleaning and parsing pipeline. Returns:
```python
{
    "input_text": str,    # Original input before cleaning
    "cents": int,         # Total cents after rounding
    "dollars": float,     # Rounded dollar amount (float)
    "rounded": bool,      # True if input had sub-cent precision
}
```

**Input disambiguation table:**

| Input | `$` present | Length | Interpretation | Cents |
|---|---|---|---|---|
| `"14.73"` | No | — | Decimal → dollars | 1473 |
| `"$14.73"` | Yes | — | Decimal → dollars | 1473 |
| `"1473"` | No | 4 | Raw cents | 1473 |
| `"14"` | No | 2 | Short digit → dollars | 1400 |
| `"$14"` | Yes | — | Dollar-sign → dollars | 1400 |
| `"14.735"` | No | — | Rounds to $14.74 | 1474 |

---

### `calculate_change(amount_text: str, verbose: bool = False) -> ChangeResult`

Calls `parse_amount_to_cents()`, runs greedy algorithm, builds result. Returns `ChangeResult`.

**Zero-amount handling:** Returns early with `message = "Zero dollars means there is no change to hand back."`, empty `breakdown` and `trace`, `bill_count = coin_count = 0`.

**Verification:** `verification = verification_cents / 100` — the sum of all `(denomination × count)` values divided by 100. Should always equal `parsed["dollars"]` for valid US denominations.

---

### `print_denomination_info() -> None`
Iterates `sorted(DENOMINATIONS, reverse=True)`. Prints: `display_value`, `name`, `type`.

---

### `print_change_result(result: ChangeResult, verbose: bool = False) -> None`
Renders the result in three sections:
1. **Bills table** — only `type == "bill"` entries from breakdown
2. **Coins table** — only `type == "coin"` entries from breakdown
3. **Summary** — bill count, coin count, verification total, unused denominations
4. **Greedy trace** (if `verbose=True` and trace is non-empty) — step-by-step table

---

### `menu() -> None`
Interactive loop with four options: Calculate change, Toggle verbose mode, View denomination info, Quit. Starts with `verbose = True`.

---

## `GreedyTraceStep` Schema

```python
{
    "denomination": int,   # Cent value (e.g., 2000 for $20)
    "name": str,           # Human name (e.g., "$20 bill")
    "before": int,         # Remaining cents before this step
    "count": int,          # How many of this denomination were used
    "after": int,          # Remaining cents after this step
}
```

One step is recorded per denomination when `verbose=True`, including denominations with `count=0`.

---

## Greedy Algorithm Correctness for US Denominations

The greedy algorithm produces the minimum number of pieces because the US denomination set has the **canonical property**: each denomination is a multiple of all smaller denominations (or close enough that no smaller combination ever outperforms the greedy choice). Specifically, $1 covers all coin combinations; $5 covers all $1-level combinations; and so on up to $100.

This property does not hold for all denomination sets. A set `{1, 3, 4}` for amount `6` would give greedy `{4, 1, 1}` (3 pieces) vs optimal `{3, 3}` (2 pieces). The module docstring notes this limitation.


---


# Interface Design Specification
## App 09 — Change Maker
**Ledger Logic Group | Document 3 of 5**

---

## Public API

### Primary Functions

```python
parse_amount_to_cents(amount_text: str) -> ParsedAmountToCents
```
```python
calculate_change(amount_text: str, verbose: bool = False) -> ChangeResult
```

**Raises:** `ValueError` for: empty input, negative amounts, scientific notation, non-numeric characters.

---

### CLI Entry Point

```bash
python change_maker.py
```

Interactive menu loop. Verbose mode is on by default.

---

## `ChangeResult` Schema

```python
{
    "ok": bool,
    "cents": int,                       # Total cents
    "amount": float,                    # Rounded dollar amount
    "rounded": bool,                    # True if input was sub-cent
    "breakdown": dict[int, int],        # {cent_value: count}
    "trace": list[GreedyTraceStep],     # Empty unless verbose=True
    "bill_count": int,                  # Total bill pieces
    "coin_count": int,                  # Total coin pieces
    "verification": float,              # Sum of (value × count) / 100
    "used_denominations": set[int],     # Denominations with count > 0
    "unused_denominations": set[int],   # Denominations with count == 0
    "message": str,                     # Non-empty only for zero-amount
}
```

---

## `ParsedAmountToCents` Schema

```python
{
    "input_text": str,
    "cents": int,
    "dollars": float,
    "rounded": bool,
}
```

---

## Input/Output Examples

### Standard decimal input
```python
result = calculate_change("14.73")
# result["cents"]:        1473
# result["breakdown"]:    {1000: 1, 200: 0, ..., 25: 1, 10: 2, 5: 0, 1: 3}
# Actual: {1000: 1, 25: 1, 10: 2, 1: 3}
# breakdown: {1000:1, 25:1, 10:2, 1:3}
# bill_count: 1, coin_count: 6
# verification: 14.73
```

### Dollar sign input
```python
result = calculate_change("$5.00")
# breakdown: {500: 1}
# bill_count: 1, coin_count: 0
```

### Raw cents input (no $ sign, length > 2)
```python
result = calculate_change("1473")
# Interpreted as 1473 cents = $14.73
# Same breakdown as "14.73"
```

### Rounding input
```python
result = calculate_change("14.735")
# result["rounded"]: True
# result["cents"]: 1474  ($14.74 after ROUND_HALF_UP)
```

### Zero amount
```python
result = calculate_change("0")
# result["message"]: "Zero dollars means there is no change to hand back."
# result["breakdown"]: {}
# result["bill_count"]: 0
# result["coin_count"]: 0
```

### Error cases
```python
calculate_change("")         # ValueError: "Please enter an amount."
calculate_change("-5.00")    # ValueError: "Negative amounts are not allowed for change making."
calculate_change("1e2")      # ValueError: "Scientific notation is not supported..."
calculate_change("abc")      # ValueError: "That amount was not numeric..."
```

### Verbose trace output
```
Greedy trace
Step  Denomination       Before      Used      Left
------------------------------------------------------------
1     $100 bill          $14.73         0     $14.73
2     $50 bill           $14.73         0     $14.73
3     $20 bill           $14.73         0     $14.73
4     $10 bill           $14.73         1      $4.73
5     $5 bill             $4.73         0      $4.73
6     $1 bill             $4.73         0      $4.73
7     quarter             $4.73         0      $4.73
8     dime                $4.73         4      $0.73
  ... (continues)
```

---

## CLI Output Format

### Bills and coins sections
```
Change for $14.73
------------------------------------------------
Bills
Denomination        Count        Subtotal
------------------------------------------------
$10 bill                1          $10.00

Coins
Denomination        Count        Subtotal
------------------------------------------------
quarter                 1           $0.25
dime                    2           $0.20
nickel                  0           $0.00
penny                   3           $0.03

Total bills used: 1
Total coins used: 6
Verification: $14.73 adds back to the original amount.
Unused denominations this time: $100 bill, $50 bill, $20 bill, $5 bill, $1 bill, nickel
```

---

## Supported Denominations

| Value | Name | Type |
|---|---|---|
| $100.00 | $100 bill | bill |
| $50.00 | $50 bill | bill |
| $20.00 | $20 bill | bill |
| $10.00 | $10 bill | bill |
| $5.00 | $5 bill | bill |
| $1.00 | $1 bill | bill |
| $0.25 | quarter | coin |
| $0.10 | dime | coin |
| $0.05 | nickel | coin |
| $0.01 | penny | coin |

Not included: half-dollar ($0.50), $2 bill, $1 coin. These are excluded because they are uncommon in standard US cash drawers.


---


# Runbook
## App 09 — Change Maker
**Ledger Logic Group | Document 4 of 5**

---

## Requirements

- Python 3.10 or later
- No third-party dependencies
- `schemas.py` and `storage.py` must be in the same directory or on `PYTHONPATH`
- `typing_extensions` for `schemas.py` (Python < 3.11)

---

## Installation

```bash
git clone https://github.com/PrincetonAfeez/ledger-logic
cd ledger-logic/change_maker
pip install typing_extensions   # Only if Python < 3.11
```

---

## Running the CLI

### Interactive menu
```bash
python change_maker.py
```

Verbose mode is on by default. Option 2 toggles it off/on.

---

## Using as a Library

### Basic change calculation
```python
from change_maker import calculate_change

result = calculate_change("14.73")
print(f"Bills: {result['bill_count']}, Coins: {result['coin_count']}")
print(f"Verified: ${result['verification']:.2f}")
```

### With verbose trace
```python
from change_maker import calculate_change, print_change_result

result = calculate_change("14.73", verbose=True)
print_change_result(result, verbose=True)
```

### Parse only (no breakdown)
```python
from change_maker import parse_amount_to_cents

parsed = parse_amount_to_cents("$14.73")
print(parsed["cents"])    # 1473
print(parsed["rounded"])  # False
```

### Handle errors
```python
from change_maker import calculate_change

try:
    result = calculate_change(user_input)
    print(f"Change: {result['breakdown']}")
except ValueError as error:
    print(f"Input error: {error}")
```

### Check if rounding occurred
```python
from change_maker import parse_amount_to_cents

parsed = parse_amount_to_cents("14.735")
if parsed["rounded"]:
    print(f"Note: rounded to ${parsed['dollars']:.2f}")
```

### Iterate breakdown programmatically
```python
from change_maker import calculate_change, DENOMINATIONS

result = calculate_change("87.43")
for cent_value, count in sorted(result["breakdown"].items(), reverse=True):
    name = DENOMINATIONS[cent_value]["name"]
    subtotal = (cent_value * count) / 100
    print(f"{name}: {count} × ${cent_value/100:.2f} = ${subtotal:.2f}")
```

---

## Running Tests

No dedicated test file was uploaded for App 09. Manual verification:

```bash
python change_maker.py
# Select 1, enter "14.73"
# Confirm: 1×$10 bill, 1×quarter, 2×dimes, 3×pennies
# Confirm: verification $14.73
# Select 2 (toggle verbose off)
# Select 1, enter "1473"
# Confirm same result (raw cents interpretation)
```

---

## Troubleshooting

### `ValueError: Scientific notation is not supported`
Enter the amount as a plain decimal: `14.73` not `1.473e1`.

### `ValueError: Negative amounts are not allowed`
Change making requires a positive amount. The module does not support "making change for a refund" — negate the amount before calling.

### Input `"100"` returns $100.00 instead of $1.00
Digit-only strings without a `$` and with length > 2 are treated as raw cents. `"100"` → 100 cents → $1.00 only if length is exactly 3. For `"100"` (3 digits), it returns 100 cents = $1.00. For `"1000"` (4 digits), it returns 1000 cents = $10.00. To force dollars, use `"$100"` or `"100.00"`.

### Breakdown is empty
Amount was zero. Check `result["message"]` — it will contain the zero-amount explanation.

### Verification does not equal original amount
This should not occur with the standard US denomination set. If it does, the `parse_amount_to_cents()` rounding produced a value that cannot be exactly represented in integer cents — check the `rounded` flag.


---


# Lessons Learned
## App 09 — Change Maker
**Ledger Logic Group | Document 5 of 5**

---

## Why This Design Was Chosen

The integer-cents approach was the central design decision. The first mental model for this module was to divide dollar amounts by denomination values in float arithmetic. A quick test showed the problem: `14.73 % 0.25` in Python produces `0.22999999999999998`, not `0.23`. Integer arithmetic is exact: `1473 % 25 == 23`. The entire module is built around this insight — convert to integers first, do all arithmetic in integers, convert back to display only.

The `verbose` trace flag came from thinking about who uses a change maker app. A cashier wants the answer only. A student learning about greedy algorithms wants to see every step. Both are valid use cases. The trace is computed during the main greedy loop so there is no performance penalty for running without it — `if verbose:` gates the step recording.

---

## What Was Intentionally Omitted

**Half-dollar and $1 coin:** These are omitted because they are not in standard US retail cash drawers. The docstring notes this explicitly. Adding them requires only two new entries in `DENOMINATIONS`.

**Optimal change for arbitrary denomination sets:** The greedy algorithm is not universally optimal. For the standard US denomination set it produces the minimum count — this is a proven mathematical property of the canonical denomination structure. A dynamic programming solution (which IS optimal for any denomination set) was considered and rejected because: (1) it is not needed for US denominations, (2) the learning goal of this module is the greedy algorithm and integer arithmetic, not DP.

**Change calculation for multiple transactions:** The module handles one amount per call. A batch mode that processes a list of amounts and reports aggregate denomination totals (e.g., "how many $20 bills do I need to start today's drawer?") would be useful but was out of scope.

**Non-US currency support:** Cent-based currencies (Euros, British pence) would work with minimal changes to `DENOMINATIONS` — their denomination structures are similar to US. Non-decimal currencies (e.g., old British pounds/shillings/pence) would require a different data model.

---

## Biggest Weakness

The three-mode digit-only input disambiguation is the most fragile part of the parser. The length-based heuristic — `len(cleaned) <= 2` treats as dollars, `> 2` treats as cents — works for common inputs but has edge cases:

- `"99"` → $99.00 (length 2, treated as dollars) ✓
- `"100"` → $1.00 (length 3, treated as cents) — a user entering "$100" without the symbol would be surprised
- `"9999999"` → $99,999.99 (7-digit raw cents) — works but is not obvious

The correct fix is to require explicit disambiguation: always use `"$"` for dollars or `"."` for decimal amounts. The length heuristic is a convenience shortcut that trades correctness for usability in the POS use case. It is documented but not ideal.

---

## Scaling Considerations

**If the denomination set changes:** Only `DENOMINATIONS` needs updating. The greedy algorithm, trace, verification, and print functions all read from the dict — they adapt automatically.

**If DP optimality is needed:** Replace the greedy loop with a standard DP coin change solution. The `parse_amount_to_cents()` and result schema (`ChangeResult`) do not need to change — the algorithm is isolated inside `calculate_change()`.

**If batch processing is needed:** Wrap `calculate_change()` in a list comprehension or `map()` call. The function is stateless and side-effect-free — safe for parallel or batch use.

---

## What the Next Refactor Would Be

1. **Remove length-based heuristic** — require `"$"` prefix for dollars or `"."` for decimal. Remove the `len(cleaned) <= 2` branch.
2. **Add half-dollar and $1 coin** as optional `DENOMINATIONS` entries controlled by a config flag.
3. **Batch mode** — `calculate_change_batch(amounts: list[str]) -> list[ChangeResult]` with aggregate stats.
4. **DP optimal mode** — `calculate_change(amount, algorithm="greedy" | "optimal")` that switches between the greedy and DP approaches.

---

## What This Project Taught

**Integer arithmetic is not an optimization — it is a correctness requirement for currency.** The transition from `float % float` to `int % int` was not a performance choice; it was the fix for a mathematically incorrect result. Any currency calculation that uses float division or modulo will produce wrong answers for amounts that cannot be represented exactly in binary floating point. The correct approach — convert to cents, do integer arithmetic, convert back — applies to any cash-handling code.

**A dict as a system specification.** `DENOMINATIONS` is not just a lookup table — it is the specification of the module's scope. It answers "what denominations does this module handle?" in a single place that is read by the algorithm, the verifier, the printer, and the denominations info display. Changing the scope requires changing exactly one data structure.

**The verification step is not optional.** Adding `verification = verification_cents / 100` and checking it against `parsed["dollars"]` turned the function into a self-checking algorithm. If the greedy algorithm ever produced a wrong result (impossible for US denominations, but possible if `DENOMINATIONS` were incorrectly modified), the verification would catch it. Building correctness checks into the result schema is a habit worth forming.

---

*Constitution v2.0 checklist: This document satisfies Article 5 (trade-off documentation) for App 09.*
