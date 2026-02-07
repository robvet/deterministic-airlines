"""
Seat Models - Request/Response schemas for seat operations.

=============================================================================
STRUCTURED DATA OUTPUT (NO NATURAL LANGUAGE)
=============================================================================

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)

ARCHITECTURAL PATTERN:
  - Tool returns STRUCTURED DATA (seat facts, reasoning)
  - Orchestrator generates NATURAL LANGUAGE from structured data
  - Single point of NL generation for consistency and control
=============================================================================
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class SeatRequest(BaseModel):
    """
    Request for seat-related operations.
    
    Covers: seat selection, changes, special service requests.
    """
    confirmation_number: Optional[str] = Field(
        default=None,
        description="Booking confirmation code"
    )
    flight_number: Optional[str] = Field(
        default=None,
        description="Flight number"
    )
    requested_seat: Optional[str] = Field(
        default=None,
        description="Specific seat requested (e.g., '14A', '2B')"
    )
    preference: Optional[str] = Field(
        default=None,
        description="Seat preference: window, aisle, front, exit row"
    )
    special_needs: Optional[str] = Field(
        default=None,
        description="Special service needs: wheelchair, medical, extra legroom"
    )
    question: str = Field(
        description="The user's seat-related request"
    )


class SeatResponse(BaseModel):
    """
    Response to seat operations.
    
    Returns STRUCTURED DATA - Orchestrator generates natural language.
    """
    success: bool = Field(
        description="Whether the seat operation was successful"
    )
    seat_number: Optional[str] = Field(
        default=None,
        description="Assigned or selected seat number"
    )
    previous_seat: Optional[str] = Field(
        default=None,
        description="Previous seat if this was a change"
    )
    seat_facts: List[str] = Field(
        description="Structured facts about the seat operation result"
    )
    reasoning: str = Field(
        description="Tool's reasoning about how the result was determined"
    )
    special_service_noted: bool = Field(
        default=False,
        description="Whether special service request was noted"
    )
