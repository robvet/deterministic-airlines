"""
FAQ Response Model - Output schema for the FAQ tool.

=============================================================================
STRUCTURED LLM OUTPUT
=============================================================================

This model defines what the LLM MUST return when answering FAQ questions.
The LLMService parses the LLM's JSON response into this Pydantic model.

If the LLM returns malformed JSON or missing fields → ValidationError
If the LLM returns wrong types (string for confidence) → ValidationError

This is how we make LLM responses DETERMINISTIC and RELIABLE.

HOW IT WORKS:
  1. FAQTool sends prompt to LLM with this schema in the instructions
  2. LLM returns raw JSON text: {"answer": "...", "confidence": 0.9, ...}
  3. LLMService parses JSON and constructs FAQResponse(...)
  4. Pydantic validates all fields against constraints
  5. If valid → returns FAQResponse object
  6. If invalid → raises ValidationError (caught and handled)

THE LLM SEES THE SCHEMA:
  When using structured output, the LLM receives the Pydantic schema
  converted to JSON Schema format. It knows exactly what to return.
=============================================================================
"""

from pydantic import BaseModel, Field


class FAQResponse(BaseModel):
    """
    Output from the FAQ tool.
    
    The LLM must return JSON matching this exact structure:
    {
        "answer": "You can bring one carry-on bag up to 22 pounds...",
        "confidence": 0.95,
        "source_topic": "baggage"
    }
    
    VALIDATION RULES:
    - answer: Required, must not be empty (min_length=1)
    - confidence: Required, must be 0.0-1.0 (ge/le constraints)
    - source_topic: Optional, can be null (str | None)
    """
    
    # ==========================================================================
    # ANSWER: The response to show the user
    # ==========================================================================
    # This is the main output - the answer to their FAQ question.
    # The LLM generates this based on the grounding data (FAQ knowledge base).
    # ==========================================================================
    answer: str = Field(
        min_length=1,  # Cannot be empty - must provide an answer
        description="The answer to the user's question"
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
