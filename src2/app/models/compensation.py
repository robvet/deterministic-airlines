"""
Compensation Models - Request/Response schemas for compensation operations.

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class CompensationRequest(BaseModel):
    """
    Request for compensation due to flight disruptions.
    
    Covers: delays, cancellations, missed connections, denied boarding.
    """
    confirmation_number: Optional[str] = Field(
        default=None,
        description="Booking confirmation code"
    )
    flight_number: Optional[str] = Field(
        default=None,
        description="Affected flight number"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for compensation: delay, cancellation, missed connection"
    )
    question: str = Field(
        description="The user's compensation request"
    )


class CompensationResponse(BaseModel):
    """
    Response to compensation requests.
    """
    case_opened: bool = Field(
        description="Whether a compensation case was opened"
    )
    case_id: Optional[str] = Field(
        default=None,
        description="Compensation case ID"
    )
    vouchers: List[str] = Field(
        default_factory=list,
        description="List of issued vouchers (hotel, meal, transport)"
    )
    total_value: Optional[float] = Field(
        default=None,
        description="Total compensation value in dollars"
    )
    message: str = Field(
        description="Human-readable result message"
    )
    next_steps: Optional[str] = Field(
        default=None,
        description="What the customer should do next"
    )
