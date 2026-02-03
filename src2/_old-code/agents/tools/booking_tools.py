"""Booking domain tools - New bookings, rebookings, cancellations."""
from __future__ import annotations as _annotations

import random
import string
from copy import deepcopy

from agents import RunContextWrapper, function_tool
from chatkit.types import ProgressUpdateEvent

from ..context import AirlineAgentChatContext
from ..demo_data import active_itinerary, apply_itinerary_defaults


@function_tool(
    name_override="book_new_flight",
    description_override="Book a new or replacement flight and auto-assign a seat."
)
async def book_new_flight(
    context: RunContextWrapper[AirlineAgentChatContext], flight_number: str | None = None
) -> str:
    """Book a replacement flight using mock inventory and update context."""
    await context.context.stream(ProgressUpdateEvent(text="Booking replacement flight..."))
    ctx_state = context.context.state
    scenario_key, itinerary = active_itinerary(ctx_state)
    apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
    options = itinerary.get("rebook_options", [])
    selection = None
    if flight_number:
        selection = next(
            (opt for opt in options if opt.get("flight_number", "").lower() == flight_number.lower()),
            None,
        )
    if selection is None and options:
        selection = options[0]
    if selection is None:
        seat = ctx_state.seat_number or "auto-assign"
        confirmation = ctx_state.confirmation_number or "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
        ctx_state.confirmation_number = confirmation
        await context.context.stream(ProgressUpdateEvent(text="Booked placeholder flight"))
        return (
            f"Booked flight {flight_number or 'TBD'} with confirmation {confirmation}. "
            f"Seat assignment: {seat}."
        )
    ctx_state.flight_number = selection.get("flight_number")
    ctx_state.seat_number = selection.get("seat") or ctx_state.seat_number or "auto-assign"
    ctx_state.itinerary = ctx_state.itinerary or deepcopy(itinerary.get("segments", []))
    updated_itinerary = [
        seg
        for seg in ctx_state.itinerary
        if not (
            scenario_key == "disrupted"
            and seg.get("origin", "").startswith("New York")
            and seg.get("destination", "").startswith("Austin")
        )
    ]
    updated_itinerary.append(
        {
            "flight_number": selection["flight_number"],
            "origin": selection.get("origin", ""),
            "destination": selection.get("destination", ""),
            "departure": selection.get("departure", ""),
            "arrival": selection.get("arrival", ""),
            "status": "Confirmed replacement flight",
            "gate": "TBD",
        }
    )
    ctx_state.itinerary = updated_itinerary
    confirmation = ctx_state.confirmation_number or "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    ctx_state.confirmation_number = confirmation
    await context.context.stream(
        ProgressUpdateEvent(
            text=f"Rebooked to {selection['flight_number']} with seat {ctx_state.seat_number}",
        )
    )
    return (
        f"Rebooked to {selection['flight_number']} from {selection.get('origin')} to {selection.get('destination')}. "
        f"Departure {selection.get('departure')}, arrival {selection.get('arrival')} (next day arrival in Austin). "
        f"Seat assigned: {ctx_state.seat_number}. Confirmation {confirmation}."
    )


@function_tool(
    name_override="cancel_flight",
    description_override="Cancel a flight."
)
async def cancel_flight(
    context: RunContextWrapper[AirlineAgentChatContext]
) -> str:
    """Cancel the flight in the context."""
    apply_itinerary_defaults(context.context.state)
    fn = context.context.state.flight_number
    assert fn is not None, "Flight number is required"
    confirmation = context.context.state.confirmation_number or "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    context.context.state.confirmation_number = confirmation
    return f"Flight {fn} successfully cancelled for confirmation {confirmation}"
