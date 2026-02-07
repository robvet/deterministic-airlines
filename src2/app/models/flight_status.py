"""
Flight Status Models - Request/Response schemas for flight status operations.

=============================================================================
STRUCTURED DATA OUTPUT (NO NATURAL LANGUAGE)
=============================================================================

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)

ARCHITECTURAL PATTERN:
  - Tool returns STRUCTURED DATA (status facts, reasoning)
  - Orchestrator generates NATURAL LANGUAGE from structured data
  - Single point of NL generation for consistency and control
=============================================================================
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class FlightStatusRequest(BaseModel):
    """
    Request to check flight status.
    
    The LLM extracts the flight number from the user's message.
    """
    flight_number: Optional[str] = Field(
        default=None,
        description="The flight number to check (e.g., 'PA441', 'DA100')"
    )
    confirmation_number: Optional[str] = Field(
        default=None,
        description="Booking confirmation code to look up flight"
    )


class FlightStatusResponse(BaseModel):
    """
    Structured output from the FlightStatus tool.
    
    NOTE: No 'message' field. The Orchestrator generates natural language
    from the structured status_facts. This ensures consistent NL generation.
    """
    found: bool = Field(
        description="Whether the flight was found"
    )
    status_facts: List[str] = Field(
        description="List of flight status details (flight, route, times, gate, warnings)"
    )
    reasoning: str = Field(
        description="Brief explanation of the status lookup result"
    )
    flight_number: Optional[str] = Field(
        default=None,
        description="The flight number"
    )
    origin: Optional[str] = Field(
        default=None,
        description="Departure airport/city"
    )
    destination: Optional[str] = Field(
        default=None,
        description="Arrival airport/city"
    )
    status: Optional[str] = Field(
        default=None,
        description="Current flight status (On time, Delayed, Cancelled)"
    )
    departure_time: Optional[str] = Field(
        default=None,
        description="Scheduled departure time"
    )
    arrival_time: Optional[str] = Field(
        default=None,
        description="Scheduled arrival time"
    )
    gate: Optional[str] = Field(
        default=None,
        description="Departure gate"
    )
