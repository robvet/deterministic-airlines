"""FAQ domain tools - Policy and information lookup."""
from __future__ import annotations as _annotations

from agents import function_tool


@function_tool(
    name_override="faq_lookup_tool", description_override="Lookup frequently asked questions."
)
async def faq_lookup_tool(question: str) -> str:
    """Lookup answers to frequently asked questions."""
    q = question.lower()
    if "bag" in q or "baggage" in q:
        return (
            "You are allowed to bring one bag on the plane. "
            "It must be under 50 pounds and 22 inches x 14 inches x 9 inches. "
            "If a bag is delayed or missing, file a baggage claim and we will track it for delivery."
        )
    if "compensation" in q or "delay" in q or "voucher" in q:
        return (
            "For lengthy delays we provide duty-of-care: hotel and meal vouchers plus ground transport where needed. "
            "If the delay is over 3 hours or causes a missed connection, we also open a compensation case and can offer miles or travel credit. "
            "A Refunds & Compensation agent can submit the case and share the voucher details with you."
        )
    elif "seats" in q or "plane" in q:
        return (
            "There are 120 seats on the plane. "
            "There are 22 business class seats and 98 economy seats. "
            "Exit rows are rows 4 and 16. "
            "Rows 5-8 are Economy Plus, with extra legroom."
        )
    elif "wifi" in q:
        return "We have free wifi on the plane, join Airline-Wifi"
    return "I'm sorry, I don't know the answer to that question."
