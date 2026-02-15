"""
Reflection Evaluator - Assesses whether the user's full request is satisfied.

After each tool execution in the orchestrator loop, this service evaluates
the structured tool results against the original user input to determine
if additional steps are needed.

Uses the fast SLM (gpt-4.1-mini) — this is a simple yes/no assessment,
not complex reasoning.
"""

from ..models.reflection import ReflectionResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService


class ReflectionEvaluator:
    """
    Evaluates whether the user's request has been fully satisfied
    after one or more tool executions.

    Called by the orchestrator after each tool execution.
    Returns a ReflectionResponse that drives the loop decision.
    """

    def __init__(
        self,
        llm_service: LLMService,
        template_service: PromptTemplateService
    ):
        self._llm = llm_service
        self._templates = template_service
        print(f"[ReflectionEvaluator] Initialized")

    def evaluate(
        self,
        original_input: str,
        executed_steps: list[dict]
    ) -> ReflectionResponse:
        """
        Assess whether the user's full request has been addressed.

        Args:
            original_input: The user's original message
            executed_steps: List of dicts, each with 'intent' and 'summary'
                describing what was executed so far

        Returns:
            ReflectionResponse with satisfied, remaining_request, reasoning
        """
        # Format executed steps into readable text
        steps_text = "\n".join(
            f"- Step {i+1}: Routed to '{step['intent']}' — {step['summary']}"
            for i, step in enumerate(executed_steps)
        )

        system_prompt = self._templates.load(
            "reflection_prompt",
            {
                "original_input": original_input,
                "executed_steps": steps_text
            }
        )

        response = self._llm.complete(
            system_prompt=system_prompt,
            user_message=original_input,
            response_model=ReflectionResponse,
            use_classifier_model=True  # gpt-4.1-mini
        )

        assert isinstance(response, ReflectionResponse), \
            f"Expected ReflectionResponse, got {type(response)}"

        print(f"[ReflectionEvaluator] Satisfied: {response.satisfied}")
        print(f"[ReflectionEvaluator] Reasoning: {response.reasoning}")
        if response.remaining_request:
            print(f"[ReflectionEvaluator] Remaining: {response.remaining_request}")

        return response
