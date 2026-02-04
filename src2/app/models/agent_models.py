"""
Agent Response Model - Final output from the orchestrator.

This is the standardized response that comes back from any tool execution,
wrapping the tool-specific response with common metadata.
"""

from typing import Any
from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """An entity extracted during intent classification."""
    type: str = Field(description="Entity type: destination, date, flight_number, topic, etc.")
    value: str = Field(description="The extracted value")


class AgentResponse(BaseModel):
    """
    Final response from the OrchestratorAgent.
    
    Wraps the tool-specific response with routing metadata.
    """
    # The actual response content
    answer: str = Field(description="The response to show the user")
    
    # Routing metadata (for debugging/logging)
    routed_to: str = Field(description="Which tool handled this request")
    confidence: float = Field(description="Classification confidence")
    
    # Original vs rewritten (for debugging/logging)
    original_input: str = Field(description="The raw user input")
    rewritten_input: str = Field(description="The cleaned/rewritten prompt")
    
    # Extracted entities from NER (for debugging/visibility)
    entities: list[ExtractedEntity] = Field(default_factory=list, description="Entities extracted during classification")
