"""
Orchestrator Agent - Routes user requests to the appropriate tool.

This is the main entry point for handling user requests. It:
1. Classifies intent using IntentClassifier (small model)
2. Checks confidence and handles fallback if needed
3. Routes to the appropriate tool from the registry
4. GENERATES NATURAL LANGUAGE from structured tool responses
5. Returns a standardized AgentResponse

ARCHITECTURAL PATTERN:
- Tools return STRUCTURED DATA (facts, reasoning, confidence)
- Orchestrator is the SINGLE POINT of natural language generation for outbound completions.
- This ensures consistent tone, format, and response quality

WORKSHOP OBJECTIVES DEMONSTRATED:
- Tool discovery via ToolRegistry
- Intent classification with confidence scoring
- Prompt rewriting and entity extraction
- Fallback handling for low confidence
- Centralized NL generation from structured data

DEBUGGING WALKTHROUGH:
1. Set breakpoint on process_request() - this is the main entry point
2. Step into _classifier.classify() to see intent classification
3. Watch classification.confidence to see routing decision
4. Step into _execute_tool() for high-confidence paths
5. Watch tool.build_request() and tool.execute() for tool invocation
6. Step into _nl_generator.generate() to see NL conversion
"""

from ..models.agent_models import AgentResponse
from ..models.classification import ClassificationRequest, ClassificationResponse
from ..models.context import AgentContext
from ..memory import IMemoryStore, ConversationTurn
from ..services.intent_classifier import IntentClassifier
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
    
    DEBUGGING:
    Set a breakpoint on process_request() and step through to see:
    1. Classification result (intent, confidence, entities)
    2. Confidence-based routing decision
    3. Tool instantiation from registry
    4. Tool execution
    
    This is the main orchestration loop that ties everything together.
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
        self._memory = memory_store
        
        # Create the intent classifier (uses the small/fast model)
        self._classifier = IntentClassifier(llm_service, template_service)
        
        # Create the NL response generator
        self._nl_generator = NLResponseGenerator(llm_service, template_service)
        
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
        
        DEBUGGING: This is the main entry point - set breakpoint here.
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
        # Shows what happens without deterministic routing - hallucination
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
        # STEP 0: LOAD CONVERSATION CONTEXT FROM MEMORY
        # -----------------------------------------------------------------
        # MULTI-TURN CONTEXT PATTERN:
        # Before classifying, we load prior conversation state:
        #   - session_entities: Accumulated entities across ALL turns
        #   - recent_turns: Last K turns (sliding window)
        #
        # This enables the classifier to understand follow-up questions:
        #   "What's my refund status?" → knows about prior cancellation
        #
        # WHY BEFORE CLASSIFICATION:
        # The classifier needs context to make informed routing decisions.
        # Without it, ambiguous queries route incorrectly.
        # =================================================================
        session_id = context.customer_name  # Demo uses customer_name as session
        session_entities = self._memory.get_entities(session_id)
        recent_turns = self._memory.get_turns(session_id, limit=settings.context_window_size)
        
        if session_entities or recent_turns:
            print(f"[Orchestrator] Loaded context: {len(session_entities)} entities, {len(recent_turns)} recent turns")
        
        # =================================================================
        # STEP 1: BUILD CLASSIFICATION REQUEST + CLASSIFY INTENT
        # -----------------------------------------------------------------
        # STRUCTURED REQUEST PATTERN:
        # Instead of passing loose parameters, we bundle everything into
        # a typed ClassificationRequest object. This:
        #   - Ensures type safety (Pydantic validation)
        #   - Makes the contract explicit
        #   - Enables easy testing (construct request objects)
        #
        # The classifier receives:
        #   - user_input: current turn's raw message
        #   - available_tools: registered tools for LLM to pick from
        #   - session_entities: accumulated state (e.g., booking_id)
        #   - recent_turns: sliding window of recent conversation
        #
        # Returns ClassificationResponse:
        #   - intent: "faq", "booking", etc. (which tool to use)
        #   - confidence: 0.0-1.0 (how certain the model is)
        #   - reasoning: why this intent was chosen
        #   - rewritten_prompt: cleaned/focused version of user input
        #   - entities: extracted info (dates, locations, etc.)
        # =================================================================
        available_tools = self._registry.get_routing_descriptions()
        
        classification_request = ClassificationRequest(
            user_input=user_input,
            available_tools=available_tools,
            session_entities=session_entities,
            recent_turns=recent_turns
        )
        
        classification = self._classifier.classify(classification_request)
        
        # =================================================================
        # Step 2: RECEIVE + VALIDATE CLASSIFICATION FROM INTENT
        # -----------------------------------------------------------------
        # DETERMINISTIC PATTERN: Validate inputs at every boundary.
        # Even though IntentClassifier validated before returning,
        # we validate again here. Defense in depth.
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
        # STEP 3: CONFIDENCE-BASED ROUTING DECISION
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
            # Very low confidence - don't even guess
            response = self._handle_fallback(user_input, classification)
            self._save_turn(context, user_input, response, classification)
            return response
        
        if classification.confidence < execute_threshold:
            # Medium confidence - ask for confirmation
            response = self._handle_clarification(user_input, classification)
            self._save_turn(context, user_input, response, classification)
            return response
        
        # =================================================================
        # STEP 4: VERIFY TOOL EXISTS IN REGISTRY
        # -----------------------------------------------------------------
        # Safety check: classifier might return an intent that doesn't
        # match any registered tool (e.g., hallucinated tool name).
        # If so, fall back gracefully rather than crash.
        # =================================================================
        if not self._registry.has_tool(classification.intent):
            print(f"[Orchestrator] WARNING: Unknown intent '{classification.intent}'")
            response = self._handle_fallback(user_input, classification)
            self._save_turn(context, user_input, response, classification)
            return response
        
        # =================================================================
        # STEP 5: GET TOOL FROM REGISTRY AND EXECUTE
        # -----------------------------------------------------------------
        # High confidence (>= 0.7) - execute the tool.
        # Uses the REWRITTEN prompt (cleaner, more focused).
        # Returns standardized AgentResponse.
        # NOTE: _execute_tool handles its own _save_turn call since it
        # has access to tool_reasoning from FAQResponse.
        # =================================================================
        response = self._execute_tool(user_input, classification, context)
        return response
    
    # Executes tool called by process_request after classification, returns AgentResponse
    def _execute_tool(
        self,
        original_input: str,
        classification: ClassificationResponse,
        context: AgentContext
    ) -> AgentResponse:
        """
        Get the tool from registry, execute it, and generate NL response.
        
        Called when confidence >= 0.7 (high confidence routing).
        Uses rewritten_prompt instead of original for cleaner input.
        
        ARCHITECTURAL PATTERN:
        1. Tool returns STRUCTURED DATA (facts, confidence, reasoning)
        2. Orchestrator generates NATURAL LANGUAGE from structured data
        3. Single point of NL generation ensures consistency
        """
        print(f"[Orchestrator] Routing to: {classification.intent}")
        
        # Get tool instance from registry (injects llm_service, template_service)
        tool = self._registry.get(
            classification.intent,
            llm_service=self._llm,
            template_service=self._templates
        )
        
        # =================================================================
        # Step 6: BUILD STRUCTURED REQUEST FOR TOOL
        # -----------------------------------------------------------------
        # PATTERN: Open/Closed Principle (SOLID)
        # 
        # Each tool knows how to build its own request from classification.
        # This eliminates the switch statement - tool owns its request type.
        #
        # BENEFIT: To add a new tool, you create a new class with its own
        # build_request() method. The orchestrator never needs modification.
        # - Open for extension (add new tools freely)
        # - Closed for modification (orchestrator code unchanged)
        # =================================================================
        request = tool.build_request(classification)
        print(f"[Orchestrator] ✓ Built {type(request).__name__}: '{classification.rewritten_prompt[:50]}...'")
        
        # Execute the tool - returns STRUCTURED DATA (not NL)
        tool_response = tool.execute(request, context)
        
        # =================================================================
        # Step 7: RECEIVE + VALIDATE STRUCTURED RESPONSE FROM TOOL
        # -----------------------------------------------------------------
        # DETERMINISTIC PATTERN: Validate all responses from external calls.
        # Tool responses now contain structured data, not NL answers.
        # =================================================================
        print(f"[Orchestrator] ✓ Received structured response from {classification.intent}")
        print(f"[Orchestrator]   Response type: {type(tool_response).__name__}")
        
        # =================================================================
        # Step 8: GENERATE NATURAL LANGUAGE FROM STRUCTURED DATA
        # -----------------------------------------------------------------
        # NLResponseGenerator handles NL generation (extracted class).
        # Tools return structured data, generator converts to NL.
        # =================================================================
        answer = self._nl_generator.generate(
            tool_response=tool_response,
            intent=classification.intent,
            original_question=original_input,
            context=context
        )
        print(f"[Orchestrator] ✓ Generated NL response ({len(answer)} chars)")
        
        # =================================================================
        # Step 9: BUILD FINAL AGENT RESPONSE
        # -----------------------------------------------------------------
        # Wrap the generated NL in a standardized AgentResponse.
        # This is the final output that goes back to the user.
        # =================================================================
        final_response = AgentResponse(
            answer=answer,
            routed_to=classification.intent,
            confidence=classification.confidence,
            original_input=original_input,
            rewritten_input=classification.rewritten_prompt,
            entities=[{"type": e.type, "value": e.value} for e in classification.entities]
        )
        print(f"[Orchestrator] ✓ Built AgentResponse, returning to user")
        
        # Save with tool reasoning for visibility
        tool_reasoning = getattr(tool_response, 'reasoning', None)
        self._save_turn(
            context, original_input, final_response, classification,
            tool_reasoning=tool_reasoning
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
        
        # Load message template and fill placeholders
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
        
        # Build capability list from registered tools
        available_capabilities = "- " + "\n- ".join([
            "baggage (lost bags, claims, policies)",
            "booking (search and book flights)", 
            "cancellation (cancel existing bookings)",
            "flight status (delays, gates, times)",
            "seat selection (changes, preferences)",
            "compensation (delays, disruptions)",
            "FAQs (policies, general questions)"
        ])
        
        # Load message template and fill placeholders
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
    
    # Saves conversation turn to memory with structured data for analysis and future context
    def _save_turn(
        self,
        context: AgentContext,
        user_input: str,
        response: AgentResponse,
        classification: ClassificationResponse,
        tool_reasoning: str | None = None
    ) -> None:
        """
        Save this conversation turn to memory.
        
        Called after every response, regardless of routing path.
        Uses customer_name as session_id for demo purposes.
        
        Args:
            context: Current conversation context
            user_input: Raw user input
            response: Final AgentResponse sent to user
            classification: Classification result (contains intent reasoning)
            tool_reasoning: Optional reasoning from the executed tool
        """
        # Convert entities list to dict for storage
        entities_dict = {e.type: e.value for e in classification.entities}
        
        turn = ConversationTurn(
            user_input=user_input,
            agent_response=response.answer,
            intent=classification.intent,
            confidence=classification.confidence,
            rewritten_prompt=classification.rewritten_prompt,
            entities=entities_dict,
            classification_reasoning=classification.reasoning,
            tool_reasoning=tool_reasoning
        )
        
        # Use customer_name as session_id (in production, use a real session ID)
        session_id = context.customer_name
        self._memory.save_turn(session_id, turn)
