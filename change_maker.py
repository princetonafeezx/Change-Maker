"""Optimal change calculator.

Denominations are a simplified common US cash drawer (no half-dollar or $1 coin).
"""

# Enable postponed evaluation of type annotations for forward references
from __future__ import annotations

# Import Decimal for high-precision currency math and specific rounding/error handling
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
# Import cast to inform the type checker that a value belongs to a specific type
from typing import cast

# Import custom type definitions for change results, greedy steps, and parsed data
from schemas import ChangeResult, GreedyTraceStep, ParsedAmountToCents
# Import utility to format numeric values into currency-style strings
from storage import format_money

# Define a mapping of integer cents to their display names and categories (bills vs coins)
DENOMINATIONS: dict[int, dict[str, str]] = {
    10000: {"name": "$100 bill", "type": "bill"}, # $100.00
    5000: {"name": "$50 bill", "type": "bill"},   # $50.00
    2000: {"name": "$20 bill", "type": "bill"},   # $20.00
    1000: {"name": "$10 bill", "type": "bill"},   # $10.00
    500: {"name": "$5 bill", "type": "bill"},    # $5.00
    100: {"name": "$1 bill", "type": "bill"},    # $1.00
    25: {"name": "quarter", "type": "coin"},     # $0.25
    10: {"name": "dime", "type": "coin"},        # $0.10
    5: {"name": "nickel", "type": "coin"},       # $0.05
    1: {"name": "penny", "type": "coin"},        # $0.01
}


def parse_amount_to_cents(amount_text: str) -> ParsedAmountToCents:
    """Parse user input to whole cents (sub-cent values round half away from zero)."""
    # Clean whitespace from the input and provide a default empty string if None
    original = (amount_text or "").strip()
    # Raise error if the input is empty or just whitespace
    if not original:
        raise ValueError("Please enter an amount.")

    # Check if a dollar sign was present to determine how to parse all-digit strings later
    had_dollar_symbol = "$" in original
    # Remove currency symbols and commas to get a clean numeric string
    cleaned = original.replace("$", "").replace(",", "").strip()
    # Remove leading positive signs which are mathematically valid but need stripping for digit checks
    if cleaned.startswith("+"):
        cleaned = cleaned[1:].strip()
    # Explicitly reject negative numbers as change cannot be made for them
    if cleaned.startswith("-"):
        raise ValueError("Negative amounts are not allowed for change making.")
    # Re-check if the string is empty after stripping symbols
    if not cleaned:
        raise ValueError("Please enter an amount.")
    # Reject scientific notation (e.g., 1e2) to keep input simple and predictable
    if "e" in cleaned.lower():
        raise ValueError(
            "Scientific notation is not supported. Use a plain amount like 14.73 or $14.73."
        )

    try:
        # Scenario 1: Input contains a decimal point
        if "." in cleaned:
            # Convert to Decimal for precise rounding
            decimal_amount = Decimal(cleaned)
            # Round to exactly two decimal places using the half-up method
            rounded = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            # Convert the rounded dollar amount to an integer representing total cents
            cents = int(rounded * 100)
            # Track if the original input had more than 2 decimal places (rounding occurred)
            rounded_happened = decimal_amount != rounded
            # Store the floating point version of the rounded amount
            dollars = float(rounded)
        # Scenario 2: Input is only digits
        elif cleaned.isdigit():
            # If $ was used or string is short, treat as dollars (e.g., "$14" or "12")
            if had_dollar_symbol or len(cleaned) <= 2:
                decimal_amount = Decimal(cleaned)
                rounded = decimal_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                cents = int(rounded * 100)
                rounded_happened = False
                dollars = float(rounded)
            # Otherwise, treat long digit-only strings as raw cents (e.g., "1473" -> $14.73)
            else:
                cents = int(cleaned)
                rounded_happened = False
                dollars = cents / 100
        # If the string doesn't fit numeric patterns, trigger the except block
        else:
            raise ValueError
    # Catch non-numeric characters or invalid Decimal formatting
    except (InvalidOperation, ValueError):
        raise ValueError("That amount was not numeric. Try formats like 14.73, $14.73, or 1473.") from None

    # Return a dictionary structured according to the ParsedAmountToCents schema
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
    """Run the greedy algorithm using integer cents internally."""
    # Convert the string input into structured numeric data
    parsed = parse_amount_to_cents(amount_text)
    # Extract the total cents for calculation
    cents = parsed["cents"]

    # Handle the special case where the amount is zero
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

    # Initialize variables for the greedy algorithm loop
    remaining = cents
    breakdown: dict[int, int] = {}
    trace: list[GreedyTraceStep] = []
    used_denominations: set[int] = set()

    # Iterate through denominations from highest ($100) to lowest ($0.01)
    for value in sorted(DENOMINATIONS, reverse=True):
        info = DENOMINATIONS[value]
        # Calculate how many of this denomination fit into the remaining total
        count = remaining // value
        # Calculate what remains after taking those units out
        leftover = remaining % value
        # If we used at least one of this bill/coin, record it
        if count:
            breakdown[value] = count
            used_denominations.add(value)
        # If verbose mode is on, record every step for the trace log
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
        # Update the running total for the next denomination in the loop
        remaining = leftover

    # Determine which denominations were not needed for this amount
    unused_denominations = set(DENOMINATIONS.keys()) - used_denominations
    # Initialize counters for metadata
    bill_count = 0
    coin_count = 0
    verification_cents = 0
    # Summarize the results from the breakdown dictionary
    for value, count in breakdown.items():
        # Multiply count by value to rebuild the total for verification
        verification_cents += value * count
        # Increment separate tallies for bills and coins
        if DENOMINATIONS[value]["type"] == "bill":
            bill_count += count
        else:
            coin_count += count

    # Return the full result set according to the ChangeResult schema
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
    """Show the supported US denominations."""
    # Print header for the denomination list
    print("Supported denominations")
    # Print a decorative separator line
    print("-" * 40)
    # Loop through denominations in descending order
    for value in sorted(DENOMINATIONS, reverse=True):
        info = DENOMINATIONS[value]
        # Format the cent value back into a dollar string
        display_value = format_money(value / 100)
        # Print a formatted row with value, name, and type
        print(f"{display_value:<10}{info['name']:<14}{info['type']}")


def print_change_result(result: ChangeResult, verbose: bool = False) -> None:
    """Display the change result in separate bill and coin sections."""
    # If a special message exists (like for zero amounts), show it and stop
    if result["message"]:
        print(result["message"])
        return

    # Warn the user if their input was rounded (e.g., $1.005 -> $1.01)
    if result["rounded"]:
        print("Note: the input was rounded to the nearest cent before processing.")

    # Show the total amount being processed
    print(f"Change for {format_money(result['amount'])}")
    print("-" * 48)
    print("Bills")
    # Print table header for bills
    print(f"{'Denomination':<18}{'Count':>8}{'Subtotal':>16}")
    print("-" * 48)
    # Filter and display only the bill-type denominations from the breakdown
    for value in sorted(result["breakdown"], reverse=True):
        if DENOMINATIONS[value]["type"] != "bill":
            continue
        count = result["breakdown"][value]
        print(f"{DENOMINATIONS[value]['name']:<18}{count:>8}{format_money((value * count) / 100):>16}")

    # Add a newline for visual spacing
    print()
    print("Coins")
    # Print table header for coins
    print(f"{'Denomination':<18}{'Count':>8}{'Subtotal':>16}")
    print("-" * 48)
    # Filter and display only the coin-type denominations from the breakdown
    for value in sorted(result["breakdown"], reverse=True):
        if DENOMINATIONS[value]["type"] != "coin":
            continue
        count = result["breakdown"][value]
        print(f"{DENOMINATIONS[value]['name']:<18}{count:>8}{format_money((value * count) / 100):>16}")

    # Print summary statistics
    print()
    print(f"Total bills used: {result['bill_count']}")
    print(f"Total coins used: {result['coin_count']}")
    # Confirm that the calculated change equals the input amount
    print(f"Verification: {format_money(result['verification'])} adds back to the original amount.")
    # List denominations that were skipped in the calculation
    print(f"Unused denominations this time: {', '.join(DENOMINATIONS[value]['name'] for value in sorted(result['unused_denominations'], reverse=True))}")

    # If verbose mode is active, display the step-by-step logic of the greedy algorithm
    if verbose and result["trace"]:
        print()
        print("Greedy trace")
        print(f"{'Step':<4}{'Denomination':<18}{'Before':>10}{'Used':>8}{'Left':>10}")
        print("-" * 60)
        # Iterate through the recorded trace steps
        for index, step in enumerate(result["trace"], start=1):
            before = format_money(step["before"] / 100)
            after = format_money(step["after"] / 100)
            # Print the state of the "remaining" total before and after each denomination check
            print(f"{index:<4}{step['name']:<18}{before:>10}{step['count']:>8}{after:>10}")


def menu() -> None:
    """Interactive loop for the change maker."""
    # Set default verbosity and define allowed input options
    verbose = True
    valid_choices = {"1", "2", "3", "4"}

    # Start the application loop
    while True:
        # Display the main menu
        print()
        print("LedgerLogic: Optimal Change Calculator")
        print("1. Calculate change")
        print("2. Toggle verbose mode")
        print("3. View denomination info")
        print("4. Quit")
        # Get user selection
        choice = input("Choose an option: ").strip()
        # Validate selection
        if choice not in valid_choices:
            print("Please pick one of the listed menu options.")
            continue

        # Option 1: Perform the change calculation
        if choice == "1":
            amount_text = input("Amount: ").strip()
            try:
                # Calculate the breakdown
                result = calculate_change(amount_text, verbose=verbose)
                # Print the formatted output
                print_change_result(result, verbose=verbose)
            except ValueError as error:
                # Handle and display errors from the parser
                print(error)

        # Option 2: Switch between verbose and quiet output
        elif choice == "2":
            verbose = not verbose
            mode = "verbose" if verbose else "quiet"
            print(f"Mode is now {mode}.")

        # Option 3: List all denominations handled by the system
        elif choice == "3":
            print_denomination_info()

        # Option 4: Exit the loop and close the program
        elif choice == "4":
            print("Exiting change maker.")
            break

# The main function is defined separately to allow for easier testing and potential future expansion.
def main() -> None:
    # Trigger the interactive menu
    menu()


# Standard boilerplate to ensure main() only runs if script is executed directly
if __name__ == "__main__":
    main()