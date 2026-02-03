"""
FAQ Request Model - Input schema for the FAQ tool.

=============================================================================
PYDANTIC INPUT VALIDATION
=============================================================================

This model defines what the FAQ tool REQUIRES to do its job.
When the orchestrator calls FAQTool.execute(request, context):
  - 'request' must be a valid FAQRequest
  - Pydantic validates on construction
  - Invalid input raises ValidationError immediately

Think of this as a "contract" - the tool promises to work correctly
IF you give it valid input matching this schema.

BENEFITS:
  1. Self-documenting: The schema IS the documentation
  2. Fail-fast: Bad data caught immediately, not deep in tool logic
  3. Type safety: IDE autocomplete works, refactoring is safe
  4. Testable: Easy to create valid/invalid test cases
=============================================================================
"""

from pydantic import BaseModel, Field


class FAQRequest(BaseModel):
    """
    Input to the FAQ tool.
    
    Contains the user's question (usually the rewritten_prompt from classification).
    
    Example:
        request = FAQRequest(question="What is the baggage allowance?")
        response = faq_tool.execute(request, context)
    
    VALIDATION:
        - question is REQUIRED (no default value)
        - question must be at least 1 character (min_length)
        - If empty string passed → ValidationError raised
    """
    
    # The user's question to answer
    # This is typically the rewritten_prompt from ClassificationResponse,
    # which has been cleaned up and focused by the intent classifier.
    question: str = Field(
        min_length=1,  # Cannot be empty string
        description="The user's policy or FAQ question to answer"
    )
