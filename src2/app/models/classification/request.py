"""
Classification Request Model - Structured input for intent classification.

=============================================================================
CONTEXT-AWARE CLASSIFICATION
=============================================================================

This model encapsulates everything the classifier needs to make a routing
decision, including conversation history for multi-turn context.

PATTERN FOR .NET DEVELOPERS:
Think of this like a DTO (Data Transfer Object) or Request object in MVC.
Instead of passing multiple parameters, we bundle them into a typed object.

BENEFITS:
- Type safety: Pydantic validates all fields
- Testability: Easy to construct test cases
- Extensibility: Add fields without changing signatures
- Clarity: Explicit about what classifier receives

USAGE:
    request = ClassificationRequest(
        user_input="What's the status?",
        available_tools="faq, booking, ...",
        session_entities={"booking_id": "IR-D204"},
        recent_turns=[turn1, turn2]
    )
    response = classifier.classify(request)
=============================================================================
"""
from pydantic import BaseModel, Field

from ...memory.models import ConversationTurn


class ClassificationRequest(BaseModel):
    """
    Structured request for intent classification.
    
    Contains current user input plus conversation history
    to enable context-aware routing decisions.
    
    WORKSHOP NOTE:
    This demonstrates the BEST PRACTICE of using structured
    objects for service boundaries rather than loose parameters.
    The classifier sees the full picture in one validated object.
    """
    
    # ========================================================================
    # CURRENT TURN
    # ========================================================================
    
    user_input: str = Field(
        description="Raw user message for this turn"
    )
    
    available_tools: str = Field(
        description="Formatted list of registered tools for LLM to pick from"
    )
    
    # ========================================================================
    # SESSION STATE (accumulated across all turns)
    # ========================================================================
    
    session_entities: dict[str, str] = Field(
        default_factory=dict,
        description="Accumulated entities from all prior turns (e.g., booking_id, flight)"
    )
    
    # ========================================================================
    # RECENT CONVERSATION (sliding window for context)
    # ========================================================================
    
    recent_turns: list[ConversationTurn] = Field(
        default_factory=list,
        description="Last K turns for conversation context (newest first)"
    )
    
    @property
    def has_history(self) -> bool:
        """Returns True if there's any prior conversation context."""
        return bool(self.session_entities or self.recent_turns)
    
    @property
    def turn_count(self) -> int:
        """Number of recent turns included."""
        return len(self.recent_turns)
