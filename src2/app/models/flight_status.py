"""
Flight Status Models - Request/Response schemas for flight status operations.

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)
"""
from pydantic import BaseModel, Field
from typing import Optional


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
    Response containing flight status information.
    """
    found: bool = Field(
        description="Whether the flight was found"
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
    message: str = Field(
        description="Human-readable status message"
    )
