from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import cast

from schemas import ChangeResult, GreedyTraceStep, ParsedAmountToCents
from storage import format_money
