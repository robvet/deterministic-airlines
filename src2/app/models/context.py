"""
Agent Context - Shared state across the conversation.

This object travels with every tool call, carrying customer info,
flight details, and any accumulated state from the conversation.
"""
from pydantic import BaseModel


class AgentContext(BaseModel):
    """
    Shared context for the entire conversation.
    
    Think of this as the "session state" that gets passed to every tool.
    Tools can read from it and update it as needed.
    """
    
    # Customer information
    customer_name: str = "Guest"
    
    # Flight/booking context (populated as conversation progresses)
    confirmation_number: str | None = None
    flight_number: str | None = None
    
    # Conversation tracking
    turn_count: int = 0
