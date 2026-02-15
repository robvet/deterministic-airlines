"""
Orchestrator Agent - Routes user requests to the appropriate tool.

This is the main entry point for handling user requests. It:
1. Loads conversation context via ContextManager
2. Classifies intent using IntentClassifier (black box)
3. Checks confidence and handles fallback/clarification if needed
4. Delegates tool execution to ReflectionLoop (black box)
5. Generates natural language from structured tool responses
6. Saves the turn via ContextManager

ARCHITECTURAL PATTERN:
- The orchestrator ORCHESTRATES — it does not contain feature plumbing
- IntentClassifier owns classification internals
- ReflectionLoop owns the execute-reflect-reclassify cycle
- ContextManager owns context loading, turn saving, and progressive summarization
- NLResponseGenerator owns NL generation
- The orchestrator reads data contracts (ClassificationResponse, AgentResponse)
  but has NO KNOWLEDGE of feature internals (ClassificationRequest, ReflectionEvaluator, etc.)

WORKSHOP OBJECTIVES DEMONSTRATED:
- Separation of concerns: orchestration vs. feature logic
- Black-box feature packages (intent/, reflection/)
- Confidence-based routing using data contracts
- Centralized NL generation from structured data
"""

from ..models.agent_models import AgentResponse
from ..models.classification import ClassificationResponse
from ..models.context import AgentContext
from ..memory import IMemoryStore
from ..memory.context_manager import ContextManager
from ..intent import IntentClassifier
from ..reflection import ReflectionLoop
from ..services.llm_service import LLMService
from ..services.nl_response_generator import NLResponseGenerator
from ..services.prompt_template_service import PromptTemplateService
from ..tools.tool_registry import ToolRegistry
from ..config.settings import settings


# NOTE: Confidence thresholds are loaded from settings at runtime (not module-level constants).
# This allows dynamic override via UI/API. See process_request() for threshold extraction.


class OrchestratorAgent:
    """
    Routes user requests to the appropriate tool.
    
    ARCHITECTURAL PRINCIPLE:
    The orchestrator orchestrates — it does NOT contain feature plumbing.
    Feature packages (intent/, reflection/) are black boxes.
    The orchestrator reads their output contracts but never reaches inside.
    
    DEBUGGING:
    Set a breakpoint on process_request() and step through to see:
    1. Context loading
    2. Classification result (intent, confidence, entities)
    3. Confidence-based routing decision
    4. ReflectionLoop execution (black box)
    5. NL generation from structured results
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        llm_service: LLMService,
        template_service: PromptTemplateService,
        memory_store: IMemoryStore
    ):
        self._registry = registry
        self._llm = llm_service
        self._templates = template_service
        
        # Intent classification (black box — owns classification internals)
        self._classifier = IntentClassifier(llm_service, template_service)
        
        # Context management (black box — owns turn saving + progressive summarization)
        self._context = ContextManager(memory_store, llm_service, template_service)
        
        # NL response generator
        self._nl_generator = NLResponseGenerator(llm_service, template_service)
        
        # Reflection loop (black box — owns execute-reflect-reclassify cycle)
        self._reflection_loop = ReflectionLoop(
            registry=registry,
            llm_service=llm_service,
            template_service=template_service,
            classifier=self._classifier
        )
        
        print(f"[OrchestratorAgent] Initialized")
    
    def process_request(
        self, 
        user_input: str, 
        context: AgentContext,
        bypass_classification: bool = False
    ) -> AgentResponse:
        """
        Process a user request end-to-end.
        
        Args:
            user_input: The raw user message
            context: Conversation context (customer info, turn count, etc.)
            bypass_classification: If True, skip routing and call LLM directly (for demo)
        
        Returns:
            AgentResponse with the final answer and metadata
        
        DEBUGGING: This is the main entry point — set breakpoint here.
        """
        print(f"\n[Orchestrator] Received: {user_input}")
        
        # =================================================================
        # GET CURRENT THRESHOLD VALUES
        # -----------------------------------------------------------------
        # Thresholds are loaded from settings but can be overridden per-request
        # via the API (for dashboard tuning). Extract here for readability.
        # =================================================================
        execute_threshold = settings.confidence_threshold_execute
        clarify_threshold = settings.confidence_threshold_clarify
        print(f"[Orchestrator] Thresholds: execute={execute_threshold:.2f}, clarify={clarify_threshold:.2f}")
        
        # =================================================================
        # BYPASS MODE: Skip classification, call LLM directly (for demo)
        # Shows what happens without deterministic routing — hallucination
        # =================================================================
        if bypass_classification:
            print(f"[Orchestrator] BYPASS MODE - calling LLM directly, no grounding")
            raw_response = self._llm.complete(
                system_prompt="You are a helpful customer service agent for Deterministic Airlines. Answer the customer's question to the best of your ability.",
                user_message=user_input
            )
            return AgentResponse(
                answer=raw_response,
                routed_to="bypass",
                confidence=0.0,
                original_input=user_input,
                rewritten_input=user_input,
                entities=[]
            )
        
        # =================================================================
        # STEP 1: LOAD CONVERSATION CONTEXT (black box)
        # -----------------------------------------------------------------
        # ContextManager loads prior state: summary, entities, recent turns.
        # This enables the classifier to understand follow-up questions.
        # =================================================================
        session_id = context.customer_name
        conversation_summary, session_entities, recent_turns = \
            self._context.load_context(session_id)
        
        # =================================================================
        # STEP 2: CLASSIFY INTENT (black box)
        # -----------------------------------------------------------------
        # The classifier handles all internals: request building, prompt
        # construction, SLM call, validation. We just pass simple values
        # and get back a ClassificationResponse data contract.
        #
        # Returns ClassificationResponse:
        #   - intent: "faq", "booking", etc. (which tool to use)
        #   - confidence: 0.0-1.0 (how certain the model is)
        #   - reasoning: why this intent was chosen
        #   - rewritten_prompt: cleaned/focused version of user input
        #   - entities: extracted info (dates, locations, etc.)
        # =================================================================
        available_tools = self._registry.get_routing_descriptions()
        
        classification = self._classifier.classify(
            user_input=user_input,
            available_tools=available_tools,
            session_entities=session_entities,
            recent_turns=recent_turns,
            conversation_summary=conversation_summary
        )
        
        # =================================================================
        # STEP 3: VALIDATE CLASSIFICATION CONTRACT
        # -----------------------------------------------------------------
        # Defense in depth — validate at every boundary.
        # =================================================================
        assert isinstance(classification, ClassificationResponse), \
            f"Expected ClassificationResponse, got {type(classification)}"
        assert classification.intent, "Classification must have an intent"
        assert 0.0 <= classification.confidence <= 1.0, \
            f"Confidence must be 0.0-1.0, got {classification.confidence}"
        print(f"[Orchestrator] ✓ Received valid ClassificationResponse")
        print(f"[Orchestrator]   Intent: '{classification.intent}'")
        print(f"[Orchestrator]   Available tools: {self._registry.list_tools()}")
        
        # =================================================================
        # STEP 4: CONFIDENCE-BASED ROUTING DECISION
        # -----------------------------------------------------------------
        # Three-tier decision based on confidence score:
        #
        #   confidence < clarify_threshold  → FALLBACK
        #       Model is very uncertain. Don't guess - apologize and
        #       ask user to rephrase. Avoids wrong tool execution.
        #
        #   confidence < execute_threshold → CLARIFY  
        #       Model has some idea but not confident. Ask user to
        #       confirm before executing. "Did you mean...?"
        #
        #   confidence >= execute_threshold → EXECUTE
        #       Model is confident. Proceed to tool execution.
        #
        # NOTE: Thresholds extracted above from settings (configurable via UI)
        # =================================================================
        if classification.confidence < clarify_threshold:
            response = self._handle_fallback(user_input, classification)
            self._context.save_turn(session_id, user_input, response.answer, classification)
            return response
        
        if classification.confidence < execute_threshold:
            response = self._handle_clarification(user_input, classification)
            self._context.save_turn(session_id, user_input, response.answer, classification)
            return response
        
        # =================================================================
        # STEP 5: EXECUTE WITH REFLECTION (black box)
        # -----------------------------------------------------------------
        # ReflectionLoop owns the complete execute-reflect-reclassify cycle.
        # The orchestrator has NO KNOWLEDGE of loop mechanics, step counting,
        # re-classification logic, or tool execution plumbing.
        #
        # Returns: list of (tool_response, ClassificationResponse) tuples
        #          None if initial intent is not in the tool registry
        # =================================================================
        tool_responses = self._reflection_loop.execute(
            user_input=user_input,
            initial_classification=classification,
            context=context,
            execute_threshold=execute_threshold,
            available_tools=available_tools,
            session_entities=session_entities,
            recent_turns=recent_turns,
            conversation_summary=conversation_summary
        )
        
        # If initial intent not in registry, fall back
        if tool_responses is None:
            print(f"[Orchestrator] WARNING: Unknown intent '{classification.intent}'")
            response = self._handle_fallback(user_input, classification)
            self._context.save_turn(session_id, user_input, response.answer, classification)
            return response
        
        # =================================================================
        # STEP 6: GENERATE NL FROM TOOL RESULTS
        # -----------------------------------------------------------------
        # Single tool result → existing generate() (identical to before)
        # Multiple tool results → generate_combined() for one coherent response
        # =================================================================
        if len(tool_responses) == 1:
            tool_resp, cls = tool_responses[0]
            answer = self._nl_generator.generate(
                tool_response=tool_resp,
                intent=cls.intent,
                original_question=user_input,
                context=context
            )
        else:
            answer = self._nl_generator.generate_combined(
                tool_results=tool_responses,
                original_question=user_input,
                context=context
            )
        print(f"[Orchestrator] ✓ Generated NL response ({len(answer)} chars)")
        
        # =================================================================
        # STEP 7: BUILD FINAL AGENT RESPONSE
        # -----------------------------------------------------------------
        # Wrap the generated NL in a standardized AgentResponse.
        # Uses the FIRST classification for routing metadata (primary intent).
        # =================================================================
        primary_cls = tool_responses[0][1]
        final_response = AgentResponse(
            answer=answer,
            routed_to=primary_cls.intent,
            confidence=primary_cls.confidence,
            original_input=user_input,
            rewritten_input=primary_cls.rewritten_prompt,
            entities=[{"type": e.type, "value": e.value} for e in primary_cls.entities]
        )
        print(f"[Orchestrator] ✓ Built AgentResponse, returning to user")
        
        # Save turn with tool reasoning from last executed tool
        tool_reasoning = getattr(tool_responses[-1][0], 'reasoning', None)
        self._context.save_turn(
            session_id, user_input, final_response.answer,
            classification, tool_reasoning=tool_reasoning
        )
        return final_response
    
    def _handle_clarification(
        self,
        original_input: str,
        classification: ClassificationResponse
    ) -> AgentResponse:
        """
        Handle medium-confidence (between clarify and execute) by asking for clarification.
        
        The model has some idea what the user wants, but isn't confident.
        Ask the user to confirm before executing the wrong tool.
        
        Message loaded from: prompts/clarification_message.txt
        """
        print(f"[Orchestrator] Medium confidence ({classification.confidence:.2f}) - asking clarification")
        
        template = self._templates.load("clarification_message")
        message = template.format(
            detected_intent=classification.intent,
            confidence=f"{classification.confidence:.2f}"
        )
        
        return AgentResponse(
            answer=message,
            routed_to="clarification",
            confidence=classification.confidence,
            original_input=original_input,
            rewritten_input=classification.rewritten_prompt,
            entities=[{"type": e.type, "value": e.value} for e in classification.entities]
        )
    
    def _handle_fallback(
        self,
        original_input: str,
        classification: ClassificationResponse
    ) -> AgentResponse:
        """
        Handle very low confidence (< clarify threshold) or unknown intent.
        
        The model is too uncertain to even guess. Don't risk executing
        the wrong tool - apologize and list what we CAN help with.
        
        Message loaded from: prompts/fallback_message.txt
        """
        print(f"[Orchestrator] Fallback - confidence too low ({classification.confidence:.2f})")
        
        available_capabilities = "- " + "\n- ".join([
            "baggage (lost bags, claims, policies)",
            "booking (search and book flights)", 
            "cancellation (cancel existing bookings)",
            "flight status (delays, gates, times)",
            "seat selection (changes, preferences)",
            "compensation (delays, disruptions)",
            "FAQs (policies, general questions)"
        ])
        
        template = self._templates.load("fallback_message")
        message = template.format(
            available_capabilities=available_capabilities,
            confidence=f"{classification.confidence:.2f}",
            detected_intent=classification.intent
        )
        
        return AgentResponse(
            answer=message,
            routed_to="fallback",
            confidence=classification.confidence,
            original_input=original_input,
            rewritten_input=classification.rewritten_prompt,
            entities=[{"type": e.type, "value": e.value} for e in classification.entities]
        )
