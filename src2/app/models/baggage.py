"""
Baggage Models - Request/Response schemas for baggage operations.

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class BaggageRequest(BaseModel):
    """
    Request for baggage-related inquiries.
    
    Covers: allowance, fees, lost/missing bags, policies.
    """
    query_type: Optional[Literal["allowance", "fees", "lost", "policy", "general"]] = Field(
        default="general",
        description="Type of baggage inquiry"
    )
    question: str = Field(
        description="The user's baggage-related question"
    )
    confirmation_number: Optional[str] = Field(
        default=None,
        description="Booking confirmation for lost bag claims"
    )
    baggage_tag: Optional[str] = Field(
        default=None,
        description="Baggage tag number for tracking"
    )


class BaggageResponse(BaseModel):
    """
    Response to baggage inquiries.
    """
    answer: str = Field(
        description="The answer to the baggage question"
    )
    category: str = Field(
        description="Category of inquiry: allowance, fees, lost, policy"
    )
    claim_number: Optional[str] = Field(
        default=None,
        description="Claim number if a lost bag claim was filed"
    )
    tracking_url: Optional[str] = Field(
        default=None,
        description="URL for tracking a lost bag"
    )
