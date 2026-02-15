"""
Reflection Loop - Owns the complete execute-reflect-reclassify cycle.

This is the core deterministic control that handles multi-step user requests.
The orchestrator delegates here after initial classification passes confidence
thresholds. This class is a black box — the orchestrator has NO knowledge of
the loop mechanics, step counting, or re-classification logic.

PATTERN:
1. Execute the tool for the current classification
2. Reflect: is the user's FULL request satisfied?
3. If not, re-classify the remaining request via IntentClassifier
4. Repeat (bounded by MAX_STEPS)

For single-intent requests (90%+ of cases), the loop runs once and
reflection says "satisfied" — identical to single-pass behavior.

PORTABILITY:
This class is self-contained within the reflection/ package. Give it a
ToolRegistry and IntentClassifier, and it works in any project.
"""

from ..models.classification import ClassificationResponse
from ..models.context import AgentContext
from ..tools.tool_registry import ToolRegistry
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from ..intent import IntentClassifier
from ..memory.models import ConversationTurn
from .reflection_evaluator import ReflectionEvaluator


# Maximum number of tool executions per user request.
# Bounds the loop to prevent runaway chains.
MAX_STEPS = 3


class ReflectionLoop:
    """
    Executes tools and reflects on whether the user's request is fully satisfied.

    The orchestrator calls execute() once with the initial classification.
    This class handles everything from there: tool execution, evaluation,
    re-classification, and looping.

    Returns a list of (tool_response, ClassificationResponse) tuples,
    or None if the initial intent isn't in the tool registry.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        llm_service: LLMService,
        template_service: PromptTemplateService,
        classifier: IntentClassifier
    ):
        self._registry = registry
        self._llm = llm_service
        self._templates = template_service
        self._classifier = classifier
        self._evaluator = ReflectionEvaluator(llm_service, template_service)
        print(f"[ReflectionLoop] Initialized")

    def execute(
        self,
        user_input: str,
        initial_classification: ClassificationResponse,
        context: AgentContext,
        execute_threshold: float,
        available_tools: str,
        session_entities: dict[str, str],
        recent_turns: list[ConversationTurn],
        conversation_summary: str
    ) -> list[tuple] | None:
        """
        Run the reflection loop: execute → reflect → re-classify → repeat.

        Args:
            user_input: The user's original message
            initial_classification: First classification from IntentClassifier
            context: Conversation context (customer info, etc.)
            execute_threshold: Confidence threshold for tool execution
            available_tools: Formatted tool descriptions for re-classification
            session_entities: Accumulated entities from prior turns
            recent_turns: Sliding window of recent conversation
            conversation_summary: Compressed summary of older turns

        Returns:
            List of (tool_response, ClassificationResponse) tuples on success.
            None if the initial intent is not in the tool registry.
        """
        # Verify initial tool exists in registry
        if not self._registry.has_tool(initial_classification.intent):
            print(f"[ReflectionLoop] Initial intent '{initial_classification.intent}' not in registry")
            return None

        executed_steps = []
        tool_responses = []
        current_classification = initial_classification

        for step in range(MAX_STEPS):
            # Verify tool exists (for re-classified intents after step 0)
            if step > 0 and not self._registry.has_tool(current_classification.intent):
                print(f"[ReflectionLoop] Unknown intent '{current_classification.intent}' — stopping with partial results")
                break

            # Execute tool — returns structured data only
            tool_response = self._execute_tool(current_classification, context)
            tool_responses.append((tool_response, current_classification))

            # Build step summary for reflection context
            step_summary = getattr(tool_response, 'reasoning', type(tool_response).__name__)
            executed_steps.append({
                'intent': current_classification.intent,
                'summary': step_summary
            })
            print(f"[ReflectionLoop] ✓ Step {step + 1}: executed '{current_classification.intent}'")

            # Reflect — is the user's full request satisfied?
            # Skip reflection on last allowed step (will exit loop anyway)
            if step < MAX_STEPS - 1:
                reflection = self._evaluator.evaluate(user_input, executed_steps)

                if reflection.satisfied or not reflection.remaining_request:
                    print(f"[ReflectionLoop] Satisfied after {step + 1} step(s)")
                    break

                # Re-classify the remaining request
                print(f"[ReflectionLoop] Remaining work → '{reflection.remaining_request}'")
                current_classification = self._classifier.classify(
                    user_input=reflection.remaining_request,
                    available_tools=available_tools,
                    session_entities=session_entities,
                    recent_turns=recent_turns,
                    conversation_summary=conversation_summary
                )

                # If not confident about remaining request, stop with what we have
                if current_classification.confidence < execute_threshold:
                    print(f"[ReflectionLoop] Low confidence on remaining ({current_classification.confidence:.2f}) — stopping")
                    break

        return tool_responses

    def _execute_tool(
        self,
        classification: ClassificationResponse,
        context: AgentContext
    ):
        """
        Get the tool from registry and execute it. Returns structured data only.

        PATTERN: Open/Closed Principle (SOLID)
        Each tool knows how to build its own request from classification.
        This eliminates switch statements — tool owns its request type.
        """
        print(f"[ReflectionLoop] Routing to: {classification.intent}")

        # Get tool instance from registry (injects llm_service, template_service)
        tool = self._registry.get(
            classification.intent,
            llm_service=self._llm,
            template_service=self._templates
        )

        # Build request and execute — tool owns its own request type
        request = tool.build_request(classification)
        print(f"[ReflectionLoop] ✓ Built {type(request).__name__}: '{classification.rewritten_prompt[:50]}...'")

        tool_response = tool.execute(request, context)

        print(f"[ReflectionLoop] ✓ Received {type(tool_response).__name__} from {classification.intent}")
        return tool_response
