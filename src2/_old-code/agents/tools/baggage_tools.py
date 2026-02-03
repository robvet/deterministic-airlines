"""
Baggage domain tools - Allowance, fees, lost bag claims.

NOTE: This tool exists but has no corresponding Baggage Agent yet.
This is intentional - adding the Baggage Agent is a workshop exercise.

See: docs/REFACTOR-PLAN.md - Exercise 2: Add Baggage Agent
"""
from __future__ import annotations as _annotations

from agents import function_tool


@function_tool(
    name_override="baggage_tool",
    description_override="Lookup baggage allowance and fees."
)
async def baggage_tool(query: str) -> str:
    """Lookup baggage allowance and fees."""
    q = query.lower()
    if "fee" in q:
        return "Overweight bag fee is $75."
    if "allowance" in q:
        return "One carry-on and one checked bag (up to 50 lbs) are included."
    if "missing" in q or "lost" in q:
        return "If a bag is missing, file a baggage claim at the airport or with the Baggage Agent so we can track and deliver it."
    return "Please provide details about your baggage inquiry."
