"""
Classification Response Model - Structured output from intent classification.

=============================================================================
PYDANTIC PRIMER FOR .NET DEVELOPERS
=============================================================================

Pydantic is Python's equivalent of data annotations + JSON serialization.
Think of it like:
  - C# Record types with built-in validation
  - System.ComponentModel.DataAnnotations but more powerful
  - Newtonsoft.Json with schema enforcement

KEY CONCEPTS:

1. BaseModel = Your data contract class
   - All fields are validated on construction
   - Invalid data raises ValidationError immediately
   - No need for manual null checks or try/catch

2. Field() = Attribute decorators for validation rules
   - ge=0.0 means "greater than or equal to 0.0" (like [Range(0, 1)])
   - le=1.0 means "less than or equal to 1.0"
   - min_length=1 means "string must have at least 1 character"
   - description= is for documentation AND tells the LLM what to generate

3. Literal[] = Enum-like constraint
   - Literal["faq", "booking"] means ONLY these exact strings allowed
   - If LLM returns "FAQ" or "Faq", validation fails
   - This is how we force deterministic tool routing

4. Type hints = Required vs Optional
   - field: str = Required, must be present
   - field: str | None = Optional, can be null
   - field: list[X] = List of X items
   - default_factory=list = Empty list if not provided

WHY THIS MATTERS FOR DETERMINISM:
  - LLM returns raw JSON text
  - Pydantic parses it into a validated Python object
  - If the LLM hallucinates a field or wrong type → ValidationError
  - We catch problems BEFORE they propagate through our code
=============================================================================
"""

from typing import Literal
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """
    An extracted entity from the user's input (Named Entity Recognition).
    
    The LLM extracts key information from the user's message:
      - Dates: "next Tuesday", "March 15th"
      - Locations: "Denver", "from Seattle to Boston"  
      - Flight numbers: "PA123", "flight 456"
      - Topics: "baggage", "wifi", "refund"
    
    These entities help tools understand context without re-parsing.
    
    Example JSON the LLM would return:
        {"type": "destination", "value": "Denver"}
        {"type": "date", "value": "next week"}
    """
    
    # Entity type - what kind of information this is
    # Examples: "destination", "date", "flight_number", "topic"
    type: str = Field(
        min_length=1,  # Cannot be empty string
        description="Category of entity: destination, date, flight_number, topic, etc."
    )
    
    # The actual extracted value
    # Examples: "Denver", "next Tuesday", "PA123"
    value: str = Field(
        min_length=1,  # Cannot be empty string
        description="The extracted value from user input"
    )


class ClassificationResponse(BaseModel):
    """
    Complete classification result from the IntentClassifier.
    
    This is THE critical handoff between intent classification and tool routing.
    Every field is validated to ensure deterministic behavior.
    
    The LLM must return JSON matching this EXACT structure:
    {
        "intent": "faq",
        "confidence": 0.95,
        "reasoning": "User is asking about baggage policies",
        "rewritten_prompt": "What is the baggage allowance?",
        "entities": [{"type": "topic", "value": "baggage"}]
    }
    
    VALIDATION RULES:
    - intent: Must be one of the registered tool names (Literal constraint)
    - confidence: Must be 0.0-1.0 (ge/le constraints)
    - reasoning: Must explain why (min_length constraint)
    - rewritten_prompt: Cleaned version of user input (min_length constraint)
    - entities: Optional list of extracted info (default empty list)
    """
    
    # ==========================================================================
    # INTENT: Which tool should handle this request?
    # ==========================================================================
    # Literal[] restricts to ONLY these exact string values.
    # If the LLM returns "FAQ" (uppercase) or "booking_tool", validation fails.
    # This ensures we only route to tools that actually exist.
    #
    # UPDATE THIS LIST when you add new tools to the registry!
    # ==========================================================================
    intent: Literal[
        "faq", 
        "book_flight", 
        "cancel_flight",
        "flight_status",
        "baggage",
        "seat",
        "compensation"
    ] = Field(
        description="The tool name to route to. Must be one of: faq, book_flight, cancel_flight, flight_status, baggage, seat, compensation"
    )
    
    # ==========================================================================
    # CONFIDENCE: How certain is the classification?
    # ==========================================================================
    # ge=0.0 means "greater than or equal to 0.0" (floor)
    # le=1.0 means "less than or equal to 1.0" (ceiling)
    # 
    # The orchestrator uses this for routing decisions:
    #   >= 0.7: Execute the tool confidently
    #   0.4-0.7: Ask user for clarification
    #   < 0.4: Fallback to general response
    # ==========================================================================
    confidence: float = Field(
        ge=0.0,  # Greater than or equal to 0.0
        le=1.0,  # Less than or equal to 1.0
        description="Confidence score for the classification. 0.0=no confidence, 1.0=certain"
    )
    
    # ==========================================================================
    # REASONING: Why was this intent selected?
    # ==========================================================================
    # Forcing the LLM to explain its reasoning:
    #   1. Improves classification accuracy (chain-of-thought)
    #   2. Provides debugging insight when things go wrong
    #   3. Can be logged for audit trails
    # ==========================================================================
    reasoning: str = Field(
        min_length=1,  # Cannot be empty - must explain
        description="Brief explanation of why this intent was selected"
    )
    
    # ==========================================================================
    # REWRITTEN PROMPT: Cleaned version of user input
    # ==========================================================================
    # The LLM rewrites the user's message to:
    #   - Remove noise: "um", "like", "I was wondering if maybe"
    #   - Focus the question: "What's bag policy?" → "What is the baggage allowance?"
    #   - Preserve intent: Keep the core question intact
    #
    # This rewritten version is what gets passed to the tool, not the original.
    # ==========================================================================
    rewritten_prompt: str = Field(
        min_length=1,  # Cannot be empty
        description="The user's question cleaned up: noise removed, focused, concise"
    )
    
    # ==========================================================================
    # ENTITIES: Extracted information (Named Entity Recognition)
    # ==========================================================================
    # default_factory=list means: if LLM doesn't return entities, use empty list
    # This prevents None/null issues - we always have a list to iterate over.
    #
    # Entities are passed to tools so they don't have to re-parse the question.
    # Example: User says "flight to Denver next week"
    #   → entities: [{"type": "destination", "value": "Denver"}, 
    #                {"type": "date", "value": "next week"}]
    # ==========================================================================
    entities: list[Entity] = Field(
        default_factory=list,  # Empty list if not provided (never None)
        description="Key information extracted from the user's input"
    )
