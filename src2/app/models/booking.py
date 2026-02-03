"""
Booking Models - Request/Response schemas for booking operations.

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)
"""
from pydantic import BaseModel, Field
from typing import Optional


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
    Response after booking a flight.
    
    The tool returns this structured response.
    """
    success: bool = Field(
        description="Whether the booking was successful"
    )
    confirmation_number: Optional[str] = Field(
        default=None,
        description="Booking confirmation code"
    )
    flight_number: Optional[str] = Field(
        default=None,
        description="The booked flight number"
    )
    message: str = Field(
        description="Human-readable result message"
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
    Response after cancelling a flight.
    """
    success: bool = Field(
        description="Whether the cancellation was successful"
    )
    confirmation_number: Optional[str] = Field(
        default=None,
        description="The cancelled booking's confirmation code"
    )
    refund_amount: Optional[float] = Field(
        default=None,
        description="Refund amount if applicable"
    )
    message: str = Field(
        description="Human-readable result message"
    )
