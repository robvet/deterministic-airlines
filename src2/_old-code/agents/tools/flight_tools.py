"""Flight domain tools - Status, matching flights, trip details."""
from __future__ import annotations as _annotations

from copy import deepcopy

from agents import RunContextWrapper, function_tool
from chatkit.types import ProgressUpdateEvent

from ..context import AirlineAgentChatContext
from ..demo_data import active_itinerary, apply_itinerary_defaults, get_itinerary_for_flight


@function_tool(
    name_override="get_trip_details",
    description_override="Infer the disrupted Paris->New York->Austin trip from user text and hydrate context.",
)
async def get_trip_details(
    context: RunContextWrapper[AirlineAgentChatContext], message: str
) -> str:
    """
    If the user mentions Paris, New York, or Austin, hydrate the context with the disrupted mock itinerary.
    Otherwise, hydrate the on-time mock itinerary. Returns the detected flight and confirmation.
    """
    text = message.lower()
    keywords = ["paris", "new york", "austin"]
    scenario_key = "disrupted" if any(k in text for k in keywords) else "on_time"
    apply_itinerary_defaults(context.context.state, scenario_key=scenario_key)
    ctx = context.context.state
    if scenario_key == "disrupted":
        ctx.origin = ctx.origin or "Paris (CDG)"
        ctx.destination = ctx.destination or "Austin (AUS)"
    segments = ctx.itinerary or []
    segment_summaries = []
    for seg in segments:
        segment_summaries.append(
            f"{seg.get('flight_number')} {seg.get('origin')} -> {seg.get('destination')} "
            f"status: {seg.get('status')}"
        )
    summary = "; ".join(segment_summaries) if segment_summaries else "No segment details available"
    return (
        f"Hydrated {scenario_key} itinerary: flight {ctx.flight_number}, confirmation "
        f"{ctx.confirmation_number}, origin {ctx.origin}, destination {ctx.destination}. {summary}"
    )


@function_tool(
    name_override="flight_status_tool",
    description_override="Lookup status for a flight."
)
async def flight_status_tool(
    context: RunContextWrapper[AirlineAgentChatContext], flight_number: str
) -> str:
    """Lookup the status for a flight using mock itineraries."""
    await context.context.stream(ProgressUpdateEvent(text=f"Checking status for {flight_number}..."))
    ctx_state = context.context.state
    ctx_state.flight_number = flight_number
    match = get_itinerary_for_flight(flight_number)
    if match:
        scenario_key, itinerary = match
        apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
        segments = itinerary.get("segments", [])
        rebook_options = itinerary.get("rebook_options", [])
        segment = next(
            (seg for seg in segments if seg.get("flight_number", "").lower() == flight_number.lower()),
            None,
        )
        if segment:
            route = f"{segment.get('origin', 'Unknown')} to {segment.get('destination', 'Unknown')}"
            details = [
                f"Flight {flight_number} ({route})",
                f"Status: {segment.get('status', 'On time')}",
            ]
            if segment.get("gate"):
                details.append(f"Gate: {segment['gate']}")
            if segment.get("departure") and segment.get("arrival"):
                details.append(f"Scheduled {segment['departure']} -> {segment['arrival']}")
            if scenario_key == "disrupted" and segment.get("flight_number") == "PA441":
                details.append("This delay will cause a missed connection to NY802. Reaccommodation is recommended.")
            await context.context.stream(
                ProgressUpdateEvent(text=f"Found status for flight {flight_number}")
            )
            return " | ".join(details)
        replacement = next(
            (
                seg
                for seg in rebook_options
                if seg.get("flight_number", "").lower() == flight_number.lower()
            ),
            None,
        )
        if replacement:
            route = f"{replacement.get('origin', 'Unknown')} to {replacement.get('destination', 'Unknown')}"
            seat = replacement.get("seat", "auto-assign")
            await context.context.stream(
                ProgressUpdateEvent(text=f"Found alternate flight {flight_number}")
            )
            return (
                f"Replacement flight {flight_number} ({route}) is available. "
                f"Departure {replacement.get('departure')} arriving {replacement.get('arrival')}. Seat {seat} held."
            )
    await context.context.stream(ProgressUpdateEvent(text=f"No disruptions found for {flight_number}"))
    return f"Flight {flight_number} is on time and scheduled to depart at gate A10."


@function_tool(
    name_override="get_matching_flights",
    description_override="Find replacement flights when a segment is delayed or cancelled."
)
async def get_matching_flights(
    context: RunContextWrapper[AirlineAgentChatContext],
    origin: str | None = None,
    destination: str | None = None,
) -> str:
    """Return mock matching flights for a disrupted itinerary."""
    await context.context.stream(ProgressUpdateEvent(text="Scanning for matching flights..."))
    ctx_state = context.context.state
    scenario_key, itinerary = active_itinerary(ctx_state)
    apply_itinerary_defaults(ctx_state, scenario_key=scenario_key)
    options = itinerary.get("rebook_options", [])
    if not options:
        await context.context.stream(ProgressUpdateEvent(text="No alternates needed — trip on time"))
        return "All flights are operating on time. No alternate flights are needed."
    filtered = [
        opt
        for opt in options
        if (origin is None or origin.lower() in opt.get("origin", "").lower())
        and (destination is None or destination.lower() in opt.get("destination", "").lower())
    ]
    final_options = filtered or options
    await context.context.stream(
        ProgressUpdateEvent(text=f"Found {len(final_options)} matching flight option(s)")
    )
    lines = []
    for opt in final_options:
        lines.append(
            f"{opt.get('flight_number')} {opt.get('origin')} -> {opt.get('destination')} "
            f"dep {opt.get('departure')} arr {opt.get('arrival')} | seat {opt.get('seat', 'auto-assign')} | {opt.get('note', '')}"
        )
    if scenario_key == "disrupted":
        lines.append("These options arrive in Austin the next day. Overnight hotel and meals are covered.")
    ctx_state.itinerary = ctx_state.itinerary or deepcopy(itinerary.get("segments", []))
    return "Matching flights:\n" + "\n".join(lines)
