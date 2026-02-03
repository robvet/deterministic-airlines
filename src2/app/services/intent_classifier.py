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
from ..models.classification import ClassificationResponse
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
        user_prompt: str, 
        available_tools: str # List of registered tools from the tool registry
    ) -> ClassificationResponse: # Note that ClassificationResponse is the return 
                                 # type of this method
        """
        Classify intent by sending the user prompt and available tools to an SLM
        DEBUGGING: Step into this method to see classification in action.
        """
        # =================================================================
        # STEP 0: BUILD CLASSIFICATION PROMPT
        # -----------------------------------------------------------------
        # THIS IS WHERE THE MAGIC HAPPENS - the prompt template tells
        # the LLM HOW to figure out the intent. See: prompts/intent_prompt.txt
        #
        # The template says:
        #   "You are an intent classifier. Here are AVAILABLE TOOLS: {tools}.
        #    Analyze the USER PROMPT: {user_prompt}.
        #    Pick the ONE best tool. Give a confidence score."
        #
        # So the LLM REASONS: "User said 'what's your baggage policy?'
        # That sounds like a general question → 'faq' tool, confidence 0.85"
        #
        # The LLM infers which tool description best matches the user's intent. 
        # =================================================================
        
        # Dynamically construct the system prompt for the SLM call
        system_prompt = self._templates.load(
            "intent_prompt",
            {
                "available_tools": available_tools, # registered tools for the app
                "user_prompt": user_prompt
            }
        )
        print(f"[IntentClassifier] Built classification prompt ({len(system_prompt)} chars)")
        
        # ==================================================================
        # Step 1: SLM CALL - returns structured JSON object describing user 
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
            user_message=user_prompt,
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
