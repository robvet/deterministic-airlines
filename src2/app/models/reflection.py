"""
Reflection Response Model - Structured output from the reflection evaluator.

After each tool execution, the reflection evaluator assesses whether the
user's full request has been satisfied. This drives the orchestrator's
decision to loop back for another step or proceed to NL generation.
"""

from pydantic import BaseModel, Field


class ReflectionResponse(BaseModel):
    """
    Result of reflecting on whether the user's request is fully satisfied.

    Returned by ReflectionEvaluator after each tool execution.
    The orchestrator uses 'satisfied' to decide whether to loop or exit.
    """

    satisfied: bool = Field(
        description="True if the user's full request has been addressed by the executed steps"
    )

    remaining_request: str | None = Field(
        default=None,
        description="What still needs to be done, if not satisfied. None if satisfied."
    )

    reasoning: str = Field(
        min_length=1,
        description="Brief explanation of why the request is or is not fully satisfied"
    )
