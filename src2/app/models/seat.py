"""
Seat Models - Request/Response schemas for seat operations.

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)
"""
from pydantic import BaseModel, Field
from typing import Optional


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
    message: str = Field(
        description="Human-readable result message"
    )
    special_service_noted: bool = Field(
        default=False,
        description="Whether special service request was noted"
    )
