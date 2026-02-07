"""
Booking Models - Request/Response schemas for booking operations.

=============================================================================
STRUCTURED DATA OUTPUT (NO NATURAL LANGUAGE)
=============================================================================

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)

ARCHITECTURAL PATTERN:
  - Tool returns STRUCTURED DATA (facts, reasoning)
  - Orchestrator generates NATURAL LANGUAGE from structured data
  - Single point of NL generation for consistency and control
=============================================================================
"""
from pydantic import BaseModel, Field
from typing import Optional, List


# =============================================================================
# BOOK FLIGHT MODELS
# =============================================================================

class BookFlightRequest(BaseModel):
    """
    Request to book a new flight.
    
    The LLM extracts these fields from the user's message.
    """
    flight_number: Optional[str] = Field(
        default=None,
        description="The flight number to book (e.g., 'DA100')"
    )
    origin: Optional[str] = Field(
        default=None,
        description="Departure city or airport"
    )
    destination: Optional[str] = Field(
        default=None,
        description="Arrival city or airport"
    )
    date: Optional[str] = Field(
        default=None,
        description="Travel date (YYYY-MM-DD)"
    )
    passenger_name: Optional[str] = Field(
        default=None,
        description="Name of the passenger"
    )


class BookFlightResponse(BaseModel):
    """
    Structured output from the BookFlight tool.
    
    NOTE: No 'message' field. The Orchestrator generates natural language
    from the structured booking_facts. This ensures consistent NL generation.
    """
    success: bool = Field(
        description="Whether the booking was successful"
    )
    booking_facts: List[str] = Field(
        description="List of booking details (flight, route, time, confirmation, seat)"
    )
    reasoning: str = Field(
        description="Brief explanation of the booking result"
    )
    confirmation_number: Optional[str] = Field(
        default=None,
        description="Booking confirmation code"
    )
    flight_number: Optional[str] = Field(
        default=None,
        description="The booked flight number"
    )
    seat_assignment: Optional[str] = Field(
        default=None,
        description="Assigned seat number"
    )


# =============================================================================
# CANCEL FLIGHT MODELS
# =============================================================================

class CancelFlightRequest(BaseModel):
    """
    Request to cancel an existing booking.
    
    Requires confirmation number or flight number to identify the booking.
    """
    confirmation_number: Optional[str] = Field(
        default=None,
        description="Booking confirmation code (e.g., 'IR-D204')"
    )
    flight_number: Optional[str] = Field(
        default=None,
        description="Flight number to cancel"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for cancellation"
    )


class CancelFlightResponse(BaseModel):
    """
    Structured output from the CancelFlight tool.
    
    NOTE: No 'message' field. The Orchestrator generates natural language
    from the structured cancellation_facts. This ensures consistent NL generation.
    """
    success: bool = Field(
        description="Whether the cancellation was successful"
    )
    cancellation_facts: List[str] = Field(
        description="List of cancellation details (confirmation, passenger, refund)"
    )
    reasoning: str = Field(
        description="Brief explanation of the cancellation result"
    )
    confirmation_number: Optional[str] = Field(
        default=None,
        description="The cancelled booking's confirmation code"
    )
    refund_amount: Optional[float] = Field(
        default=None,
        description="Refund amount if applicable"
    )
