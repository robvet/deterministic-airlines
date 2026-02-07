"""
Baggage Models - Request/Response schemas for baggage operations.

=============================================================================
STRUCTURED DATA OUTPUT (NO NATURAL LANGUAGE)
=============================================================================

These Pydantic models enforce structure at tool boundaries:
- Input validation (what the tool receives)
- Output validation (what the tool returns)

ARCHITECTURAL PATTERN:
  - Tool returns structured data (facts, reasoning, claim info)
  - Orchestrator generates natural language from structured data
  - Single point of NL generation for consistency and control
=============================================================================
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, List


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
    Structured output from the Baggage tool.
    
    NOTE: No 'answer' field. The Orchestrator generates natural language
    from the structured policy_facts. This ensures consistent NL generation.
    
    Example output:
    {
        "policy_facts": ["Carry-on: 22x14x9 inches", "Weight limit: 50 lbs"],
        "category": "allowance",
        "reasoning": "User asked about bag size limits",
        "claim_number": null,
        "tracking_url": null
    }
    """
    
    # ==========================================================================
    # POLICY_FACTS: Structured data from BAGGAGE_POLICIES
    # ==========================================================================
    policy_facts: List[str] = Field(
        min_length=1,
        description="List of relevant policy facts that answer the question"
    )
    
    # ==========================================================================
    # CATEGORY: Which type of baggage inquiry
    # ==========================================================================
    category: Literal["allowance", "fees", "lost", "policy"] = Field(
        description="Category of inquiry: allowance, fees, lost, policy"
    )
    
    # ==========================================================================
    # REASONING: Why these facts are relevant
    # ==========================================================================
    reasoning: str = Field(
        min_length=1,
        description="Brief explanation of why these facts answer the question"
    )
    
    # ==========================================================================
    # CLAIM_NUMBER: Only for lost bag claims
    # ==========================================================================
    claim_number: Optional[str] = Field(
        default=None,
        description="Claim number if a lost bag claim was filed"
    )
    
    # ==========================================================================
    # TRACKING_URL: Only for lost bag claims
    # ==========================================================================
    tracking_url: Optional[str] = Field(
        default=None,
        description="URL for tracking a lost bag"
    )
