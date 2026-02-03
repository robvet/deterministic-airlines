"""Compensation domain tools - Vouchers, cases, refunds."""
from __future__ import annotations as _annotations

import random

from agents import RunContextWrapper, function_tool
from chatkit.types import ProgressUpdateEvent

from ..context import AirlineAgentChatContext
from ..demo_data import active_itinerary, apply_itinerary_defaults


@function_tool(
    name_override="issue_compensation",
    description_override="Create a compensation case and issue hotel/meal vouchers."
)
async def issue_compensation(
    context: RunContextWrapper[AirlineAgentChatContext], reason: str = "Delay causing missed connection"
) -> str:
    """Open a compensation case and attach vouchers."""
    await context.context.stream(ProgressUpdateEvent(text="Opening compensation case..."))
    ctx_state = context.context.state
    scenario_key, itinerary = active_itinerary(ctx_state)
    apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
    case_id = ctx_state.compensation_case_id or f"CMP-{random.randint(1000, 9999)}"
    ctx_state.compensation_case_id = case_id
    voucher_values = list(itinerary.get("vouchers", {}).values())
    if voucher_values:
        ctx_state.vouchers = voucher_values
    else:
        ctx_state.vouchers = ctx_state.vouchers or []
    vouchers_text = "; ".join(ctx_state.vouchers) if ctx_state.vouchers else "Documented compensation with no vouchers required."
    await context.context.stream(ProgressUpdateEvent(text=f"Issued vouchers for case {case_id}"))
    return (
        f"Opened compensation case {case_id} for: {reason}. "
        f"Issued: {vouchers_text}. Keep receipts for any hotel or meal costs and attach them to this case."
    )
