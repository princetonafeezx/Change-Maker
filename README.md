# LedgerLogic — Optimal Change Calculator (`ll_change_maker`)

CLI and library code that breaks a **US cash** amount into the **minimum** number of bills and coins using the standard greedy method (valid for US denominations). Parsing uses **integer cents** internally so totals stay exact.

This folder is a **standalone slice** of the larger LedgerLogic idea: the interactive change maker, shared **`parsing`** (CSV dates/amounts), **`storage`** (atomic CSV/JSON writes, `format_money`), and **`schemas`** (TypedDict shapes for typing).

## Layout

| Module | Role |
|--------|------|
| `change_maker.py` | Parse amounts, greedy breakdown, CLI menu, printing |
| `parsing.py` | `parse_date`, `parse_amount` for bank/CSV-style strings |
| `storage.py` | `format_money`, categorized CSV + JSON helpers, data dir |
| `schemas.py` | TypedDicts for change results and categorized rows |
| `tests/` | `pytest` suite |

## Setup

```bash
cd ll_change_maker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the interactive app

From the project directory (so `import schemas` / `import storage` resolve):

```bash
python change_maker.py
```

## Tests

```bash
python -m pytest tests -q
```

## Two parsers (on purpose)

| Function | Use |
|----------|-----|
| `change_maker.parse_amount_to_cents` | **Interactive change** input: e.g. bare `1473` can mean **14.73** (total cents) when there is no `$`. |
| `parsing.parse_amount` | **CSV / bank** strings: debits in parentheses, grouping spaces; always yields a **non‑negative float** in dollars, no “integer cents” shortcut. |

Both round **half-up** to cents before use; scientific notation is rejected in both.

## Data directory (storage)

If you use `storage.get_data_dir()` without a `base_dir`, it checks the environment variable **`LEDGERLOGIC_DATA_DIR`**, otherwise creates **`./ledgerlogic_data`** under the current working directory (legacy naming from the parent app).

## Features

- **Denominations:** $100, $50, $20, $10, $5, $1 bills; quarter, dime, nickel, penny  
- **Edge cases:** zero (message, no breakdown), negatives rejected, non-numeric errors, optional note when sub-cent rounding happened  
- **Verbose mode:** step-by-step greedy trace  
- **Output:** bills vs coins, counts, verification line, unused denominations  

## Code style

Functions and dicts only (no classes in the change flow). `schemas` types are for **mypy**/readability; runtime values are plain dicts.
