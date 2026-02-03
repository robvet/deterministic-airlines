"""
Memory Models - Data structures for conversation history.

These models represent what gets stored in short-term memory.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """
    A single turn in the conversation.
    
    Stores both the user's input and the agent's response,
    along with metadata about how it was processed.
    """
    # When this turn happened
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # What the user said
    user_input: str
    
    # What the agent responded
    agent_response: str
    
    # How it was routed
    intent: str
    confidence: float
    
    # The cleaned-up version of the input
    rewritten_prompt: str
    
    # Any entities extracted (stored as dict for simplicity)
    entities: dict[str, str] = Field(default_factory=dict)
    
    # Classification reasoning (why this intent was chosen)
    classification_reasoning: str | None = None
    
    # Tool reasoning (why it answered this way)
    tool_reasoning: str | None = None
