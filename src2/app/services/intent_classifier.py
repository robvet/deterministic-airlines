"""
Intent Classifier Service - Handles intent classification, NER, and prompt rewriting.

This service uses a smaller/faster model to:
1. Classify user intent → maps to a registered tool
2. Extract entities (NER) → dates, locations, flight numbers, etc.
3. Rewrite the prompt → clean, concise, focused

All three tasks in one LLM call for efficiency.

CONFIDENCE-BASED ROUTING (consumed by Orchestrator):
=====================================================
The classifier returns a confidence score (0.0-1.0) that drives routing:

  confidence < 0.4  →  FALLBACK
      Model is very uncertain. Orchestrator apologizes and asks user
      to rephrase. Prevents wrong tool execution on unclear input.

  confidence 0.4-0.7  →  CLARIFY
      Model has some idea but isn't confident. Orchestrator asks user
      to confirm: "Did you mean...?" before executing.

  confidence >= 0.7  →  EXECUTE
      Model is confident. Orchestrator proceeds with tool execution
      using the rewritten_prompt.

Important: Note that Orchestrator, not the classifier, makes routing 
decisions based on returned confidence score.

UNKNOWN INTENTS:
================
The classifier is instructed to always return a tool name (never "unknown").
If no tool matches well, it returns the closest match with LOW CONFIDENCE,
which triggers the FALLBACK path above. This keeps the schema simple while
still handling unrecognized requests gracefully.
"""

# ClassificationResponse: A Pydantic data model that is constructed from the LLM's JSON output.
# Defines the schema: intent, confidence, reasoning, rewritten_prompt, entities
# See: app/models/classification/response.py
from ..models.classification import ClassificationRequest, ClassificationResponse
from ..memory.models import ConversationTurn
from .llm_service import LLMService
from .prompt_template_service import PromptTemplateService


class IntentClassifier:
    """
    Classifies user input and prepares it for tool routing.
    
    Uses a smaller model (gpt-4.1-mini) for fast, cheap classification.
    The heavy reasoning is left to the execution model (gpt-5.2).
    
    WORKSHOP NOTE:
    Set a breakpoint in classify() to see:
    - The classification prompt being built
    - The raw user input
    - The structured ClassificationResponse returned
    """
    
    # Constructor - requires LLM and Prompt Template services
    def __init__(
        self, 
        llm_service: LLMService, # inject LM dependency
        template_service: PromptTemplateService # inject prompt template
    ):
        self._llm = llm_service
        self._templates = template_service
        print(f"[IntentClassifier] Initialized")
    
    # Main method to classify the intent for each user input
    def classify(
        self, 
        request: ClassificationRequest  # Structured request with user input + context
    ) -> ClassificationResponse:
        """
        Classify intent by sending the user prompt and conversation context to an SLM.
        
        Args:
            request: ClassificationRequest containing user_input, available_tools,
                     session_entities (accumulated), and recent_turns (sliding window)
        
        Returns:
            ClassificationResponse with intent, confidence, entities, rewritten_prompt
        
        DEBUGGING: Step into this method to see classification in action.
        """
        # =================================================================
        # STEP 0: FORMAT CONVERSATION CONTEXT (if any history exists)
        # -----------------------------------------------------------------
        # MULTI-TURN CONTEXT PATTERN:
        # The classifier needs prior conversation to make informed routing.
        # Without context, "What's my refund status?" is ambiguous.
        # With context (prior cancellation of IR-D204), it routes correctly.
        #
        # The _format_conversation_context method builds a text block:
        #   - Session entities (accumulated state)
        #   - Recent turns (sliding window of last K turns)
        # =================================================================
        conversation_context = self._format_conversation_context(
            request.session_entities,
            request.recent_turns
        )
        if conversation_context:
            print(f"[IntentClassifier] Including conversation context ({len(request.recent_turns)} turns, {len(request.session_entities)} entities)")
        
        # =================================================================
        # STEP 1: BUILD CLASSIFICATION PROMPT
        # -----------------------------------------------------------------
        # THIS IS WHERE THE MAGIC HAPPENS - the prompt template tells
        # the LLM HOW to figure out the intent. See: prompts/intent_prompt.txt
        #
        # The template says:
        #   "You are an intent classifier. Here are AVAILABLE TOOLS: {tools}.
        #    Analyze the USER PROMPT: {user_prompt}.
        #    Pick the ONE best tool. Give a confidence score."
        #
        # Now also includes conversation context for multi-turn routing.
        # =================================================================
        
        # Dynamically construct the system prompt for the SLM call
        system_prompt = self._templates.load(
            "intent_prompt",
            {
                "available_tools": request.available_tools,
                "user_prompt": request.user_input,
                "conversation_context": conversation_context
            }
        )
        print(f"[IntentClassifier] Built classification prompt ({len(system_prompt)} chars)")
        
        # ==================================================================
        # Step 2: SLM CALL - returns structured JSON object describing user 
        # intent as opposed to unstructured text increasing determinism
        # ------------------------------------------------------------------
        #   response.intent          ← LLM's DECISION: which tool to use
        #   response.confidence      ← LLM's SELF-ASSESSMENT: how sure it is
        #   response.reasoning       ← LLM's EXPLANATION: why this tool
        #   response.rewritten_prompt← LLM's CLEANUP: polished user message
        #   response.entities        ← LLM's EXTRACTION: dates, flights, etc.
        # ==================================================================
        response = self._llm.complete(
            system_prompt=system_prompt,
            user_message=request.user_input,
            response_model=ClassificationResponse,  # LLM's JSON → Pydantic object
            use_classifier_model=True  # gpt-4.1-mini (fast/cheap)
        )
        
        # =================================================================
        # STEP 2: VALIDATE THE SLM's DECISION
        # =================================================================
        # Ensure response properties exist and are within expected ranges.
        assert isinstance(response, ClassificationResponse), \
            f"Expected ClassificationResponse, got {type(response)}"
        
        # Ensure response.intent, SLM's DECISION as to which tool handles this request
        # (not a lookup - the LLM figured this out by reading the prompt)
        assert response.intent, "Intent cannot be empty"
        
        # Ensure response.confidence score falls within 0.0-1.0
        # as it DRIVES ROUTING DECISIONS
        #   < 0.4  → Orchestrator triggers FALLBACK
        #   0.4-0.7 → Orchestrator asks CLARIFY
        #   >= 0.7 → Orchestrator proceeds with EXECUTE
        assert 0.0 <= response.confidence <= 1.0, \
            f"Confidence must be 0.0-1.0, got {response.confidence}"
        
        # response.rewritten_prompt: Cleansed user prompt passed to tool
        assert response.rewritten_prompt, "Rewritten prompt cannot be empty"
        
        # =================================================================
        # STEP 3: LOG CLASSIFICATION RESULTS (Debug/Workshop visibility)
        # =================================================================
        print(f"[IntentClassifier] ✓ Validated ClassificationResponse")
        print(f"[IntentClassifier]   Intent: {response.intent} (confidence: {response.confidence:.2f})")
        print(f"[IntentClassifier]   Reasoning: {response.reasoning}")
        print(f"[IntentClassifier]   Rewritten: {response.rewritten_prompt}")
        if response.entities:
            print(f"[IntentClassifier]   Entities: {[(e.type, e.value) for e in response.entities]}")
        
        return response
    
    def _format_conversation_context(
        self,
        session_entities: dict[str, str],
        recent_turns: list[ConversationTurn]
    ) -> str:
        """
        Format conversation history into a text block for the classifier prompt.
        
        This method builds a human-readable summary of:
        1. Session entities (accumulated state across all turns)
        2. Recent turns (sliding window of last K turns)
        
        Returns empty string if no history exists (first turn).
        
        WORKSHOP NOTE:
        This is the key to multi-turn context. The classifier sees:
        - What entities have been mentioned (booking_id, flight, etc.)
        - What topics were discussed recently
        - How the conversation has flowed
        
        This enables follow-up questions like "What about my refund?" to
        route correctly based on prior cancellation discussion.
        """
        parts = []
        
        # =====================================================================
        # SESSION ENTITIES: Accumulated state from all prior turns
        # =====================================================================
        if session_entities:
            parts.append("\nSESSION ENTITIES (known from prior conversation):")
            for entity_type, value in session_entities.items():
                parts.append(f"- {entity_type}: {value}")
        
        # =====================================================================
        # RECENT TURNS: Sliding window of last K turns for context
        # =====================================================================
        if recent_turns:
            parts.append("\nRECENT CONVERSATION (for context):")
            # recent_turns is newest-first, reverse for chronological display
            for i, turn in enumerate(reversed(recent_turns), 1):
                parts.append(f"[Turn {i}] User: \"{turn.user_input}\"")
                parts.append(f"         Routed to: {turn.intent} (confidence: {turn.confidence:.2f})")
        
        # Return formatted block or empty string
        if parts:
            parts.append("")  # trailing newline
            return "\n".join(parts)
        return ""
