"""Seat domain tools - Seat updates, special services, seat map display."""
from __future__ import annotations as _annotations

import random
import string

from agents import RunContextWrapper, function_tool

from ..context import AirlineAgentChatContext
from ..demo_data import apply_itinerary_defaults


@function_tool
async def update_seat(
    context: RunContextWrapper[AirlineAgentChatContext], confirmation_number: str, new_seat: str
) -> str:
    """Update the seat for a given confirmation number."""
    apply_itinerary_defaults(context.context.state)
    context.context.state.confirmation_number = confirmation_number
    context.context.state.seat_number = new_seat
    assert context.context.state.flight_number is not None, "Flight number is required"
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}"


@function_tool(
    name_override="assign_special_service_seat",
    description_override="Assign front row or special service seating for medical needs."
)
async def assign_special_service_seat(
    context: RunContextWrapper[AirlineAgentChatContext], seat_request: str = "front row for medical needs"
) -> str:
    """Assign a special service seat and record the request."""
    ctx_state = context.context.state
    apply_itinerary_defaults(ctx_state)
    preferred_seat = "1A" if "front" in seat_request.lower() else "2A"
    ctx_state.seat_number = preferred_seat
    ctx_state.special_service_note = seat_request
    confirmation = ctx_state.confirmation_number or "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    ctx_state.confirmation_number = confirmation
    return (
        f"Secured {seat_request} seat {preferred_seat} on flight {ctx_state.flight_number or 'upcoming segment'}. "
        f"Confirmation {confirmation} noted with special service flag."
    )


@function_tool(
    name_override="display_seat_map",
    description_override="Display an interactive seat map to the customer so they can choose a new seat."
)
async def display_seat_map(
    context: RunContextWrapper[AirlineAgentChatContext]
) -> str:
    """Trigger the UI to show an interactive seat map to the customer."""
    # The returned string will be interpreted by the UI to open the seat selector.
    return "DISPLAY_SEAT_MAP"
