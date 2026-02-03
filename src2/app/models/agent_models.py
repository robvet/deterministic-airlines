"""
Agent Response Model - Final output from the orchestrator.

This is the standardized response that comes back from any tool execution,
wrapping the tool-specific response with common metadata.
"""

from typing import Any
from pydantic import BaseModel, Field


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
