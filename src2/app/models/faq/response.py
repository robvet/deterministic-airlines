"""
FAQ Response Model - Output schema for the FAQ tool.

=============================================================================
STRUCTURED LLM OUTPUT (NO NATURAL LANGUAGE)
=============================================================================

This model defines the STRUCTURED DATA the FAQ tool LLM returns.
The tool performs grounded reasoning over the knowledge base but returns
FACTS and REASONING, not natural language. The Orchestrator is responsible
for converting this structured data into a natural language response.

ARCHITECTURAL PATTERN:
  - Tools return structured data (facts, reasoning, confidence)
  - Orchestrator generates natural language from structured data
  - Single point of NL generation for consistency and control

HOW IT WORKS:
  1. FAQTool sends prompt to LLM with knowledge base
  2. LLM reasons over knowledge base, identifies relevant facts
  3. LLM returns structured JSON: {"relevant_facts": [...], "reasoning": "...", ...}
  4. Pydantic validates the response
  5. Orchestrator receives structured data, generates NL response
=============================================================================
"""

from pydantic import BaseModel, Field
from typing import List


class FAQResponse(BaseModel):
    """
    Structured output from the FAQ tool.
    
    The LLM must return JSON matching this structure:
    {
        "relevant_facts": ["Carry-on limit: 22x14x9 inches", "Weight limit: 50 lbs"],
        "confidence": 0.95,
        "source_topic": "baggage",
        "reasoning": "User asked about luggage size, mapped to carry-on dimensions policy"
    }
    
    NOTE: No 'answer' field. The Orchestrator generates natural language
    from these structured facts.
    
    VALIDATION RULES:
    - relevant_facts: Required, list of facts from knowledge base
    - confidence: Required, must be 0.0-1.0 (ge/le constraints)
    - source_topic: Optional, can be null (str | None)
    - reasoning: Required, explains why these facts are relevant
    """
    
    # ==========================================================================
    # RELEVANT_FACTS: Structured data extracted from knowledge base
    # ==========================================================================
    # These are the specific facts from the FAQ knowledge base that answer
    # the user's question. The LLM identifies and extracts these based on
    # its grounded reasoning. The Orchestrator will convert these to NL.
    #
    # Example: ["Carry-on size: 22x14x9 inches", "One personal item included"]
    # NOTE: Can be empty if question not covered by knowledge base
    # ==========================================================================
    relevant_facts: List[str] = Field(
        default_factory=list,  # Allow empty if no matching facts
        description="List of relevant facts from the knowledge base that answer the question"
    )
    
    # ==========================================================================
    # CONFIDENCE: How certain is the answer?
    # ==========================================================================
    # The LLM self-reports confidence based on:
    #   - Was the question covered in the FAQ knowledge base?
    #   - Is the answer directly stated or inferred?
    #   - Any ambiguity in the question?
    #
    # We use this for:
    #   - Logging/analytics: Track answer quality over time
    #   - UI hints: "I'm not entirely sure, but..." for low confidence
    #   - Escalation: Low confidence might trigger human handoff
    # ==========================================================================
    confidence: float = Field(
        ge=0.0,  # Greater than or equal to 0.0 (floor)
        le=1.0,  # Less than or equal to 1.0 (ceiling)
        description="Confidence score from 0.0 (uncertain) to 1.0 (certain)"
    )
    
    # ==========================================================================
    # SOURCE TOPIC: Which FAQ category answered this?
    # ==========================================================================
    # Optional field - the LLM identifies which topic in the knowledge base
    # was used to answer the question. Useful for:
    #   - Analytics: What topics are users asking about?
    #   - Debugging: Did it use the right source?
    #   - UI: Show "From our baggage policy" attribution
    #
    # str | None means: can be a string OR null/None
    # default=None means: if LLM doesn't return it, use None
    # ==========================================================================
    source_topic: str | None = Field(
        default=None,  # Optional - can be omitted
        description="Which FAQ topic the answer came from (e.g., 'baggage', 'wifi')"
    )
    
    # ==========================================================================
    # REASONING: Why did the model answer this way?
    # ==========================================================================
    # The LLM explains its reasoning process:
    #   - Which parts of the knowledge base it used
    #   - Why it chose this answer over alternatives
    #   - Any caveats or limitations
    #
    # Critical for:
    #   - Debugging: Understanding model behavior
    #   - Auditing: Knowing why decisions were made
    #   - Transparency: Showing users why answers were given
    #   - Memory: Stored with conversation turn for context
    # ==========================================================================
    reasoning: str = Field(
        min_length=1,  # Must explain reasoning
        description="Brief explanation of why this answer was given and what sources were used"
    )
