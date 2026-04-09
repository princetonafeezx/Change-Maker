# Schema folder

These schemas are a best-fit addition for the current `Change-Maker` repo.

## Why JSON Schema?
The repository is a Python CLI/library, not a database-backed app. It already defines data contracts as Python `TypedDict`s in `schemas.py`, so the cleanest portable schema format is **JSON Schema**.

## Files
- `categorized_record.schema.json` — one categorized transaction row
- `categorized_transactions_file.schema.json` — a list of categorized transaction rows
- `greedy_trace_step.schema.json` — one verbose greedy-calculation step
- `parsed_amount_to_cents.schema.json` — parser output from `parse_amount_to_cents`
- `change_result.schema.json` — return shape from `calculate_change`

## Important translation notes
- Python `set[int]` fields in `ChangeResult` are represented as JSON arrays with `uniqueItems: true`.
- The `breakdown` field uses JSON object keys, so denomination keys are strings in JSON even though the Python code uses `int`.
- The repo has helper functions for `budget_profile.json` and `investment_scenarios.json`, but the current code does **not** define stable field-level contracts for those payloads, so no strict schema was invented for them here.

## Suggested placement
Put this `Schema/` folder at the repository root.
