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
from ..intent import IntentClassifier
from ..services.llm_service import LLMService
from ..services.nl_response_generator import NLResponseGenerator
from ..services.prompt_template_service import PromptTemplateService
from ..services.conversation_summarizer import ConversationSummarizer
from ..reflection import ReflectionEvaluator
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
        
        # Create the conversation summarizer (for progressive summarization)
        self._summarizer = ConversationSummarizer(llm_service, template_service)
        
        # Create the reflection evaluator (for multi-step intent handling)
        self._reflector = ReflectionEvaluator(llm_service, template_service)
        
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
        #   - conversation_summary: Compressed older turns (progressive summarization)
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
        conversation_summary = self._memory.get_summary(session_id)
        session_entities = self._memory.get_entities(session_id)
        recent_turns = self._memory.get_turns(session_id, limit=settings.context_window_size)
        
        if session_entities or recent_turns or conversation_summary:
            has_summary = "with summary" if conversation_summary else "no summary"
            print(f"[Orchestrator] Loaded context: {len(session_entities)} entities, {len(recent_turns)} recent turns, {has_summary}")
        
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
            recent_turns=recent_turns,
            conversation_summary=conversation_summary
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
        # STEP 4: REFLECTION LOOP — execute, reflect, re-classify if needed
        # -----------------------------------------------------------------
        # MULTI-STEP INTENT PATTERN:
        # Instead of single-pass classify→execute, we loop:
        #   1. Execute tool for current classification
        #   2. Reflect: is the user's FULL request satisfied?
        #   3. If not, re-classify the remaining request
        #   4. Repeat (bounded by MAX_STEPS)
        #
        # For single-intent requests (90%+ of cases), the loop runs once
        # and reflection says "satisfied" — identical to the old behavior.
        #
        # For multi-intent requests (e.g., "check my flight AND baggage"):
        #   Step 1: flight_status tool → reflection says "baggage not addressed"
        #   Step 2: re-classify "baggage" → baggage tool → reflection says "satisfied"
        #
        # MAX_STEPS bounds the loop to prevent runaway chains.
        # =================================================================
        MAX_STEPS = 3
        executed_steps = []
        tool_responses = []  # list of (tool_response, classification) tuples
        current_classification = classification
        
        for step in range(MAX_STEPS):
            # Verify tool exists in registry
            if not self._registry.has_tool(current_classification.intent):
                print(f"[Orchestrator] WARNING: Unknown intent '{current_classification.intent}'")
                if not tool_responses:
                    # No results yet — fallback
                    response = self._handle_fallback(user_input, current_classification)
                    self._save_turn(context, user_input, response, classification)
                    return response
                break  # Have partial results, proceed to NL generation
            
            # Execute tool — returns structured data only
            tool_response = self._run_tool(current_classification, context)
            tool_responses.append((tool_response, current_classification))
            
            # Build step summary for reflection context
            step_summary = getattr(tool_response, 'reasoning', type(tool_response).__name__)
            executed_steps.append({
                'intent': current_classification.intent,
                'summary': step_summary
            })
            print(f"[Orchestrator] ✓ Step {step + 1}: executed '{current_classification.intent}'")
            
            # Reflect — is the user's full request satisfied?
            # Skip reflection on last allowed step (will exit loop anyway)
            if step < MAX_STEPS - 1:
                reflection = self._reflector.evaluate(user_input, executed_steps)
                
                if reflection.satisfied or not reflection.remaining_request:
                    print(f"[Orchestrator] Reflection: satisfied after {step + 1} step(s)")
                    break
                
                # Re-classify the remaining request
                print(f"[Orchestrator] Reflection: remaining work → '{reflection.remaining_request}'")
                remaining_request = ClassificationRequest(
                    user_input=reflection.remaining_request,
                    available_tools=available_tools,
                    session_entities=session_entities,
                    recent_turns=recent_turns,
                    conversation_summary=conversation_summary
                )
                current_classification = self._classifier.classify(remaining_request)
                
                # If not confident about remaining request, stop with what we have
                if current_classification.confidence < execute_threshold:
                    print(f"[Orchestrator] Low confidence on remaining ({current_classification.confidence:.2f}) — stopping")
                    break
        
        # =================================================================
        # STEP 5: GENERATE NL FROM ACCUMULATED TOOL RESULTS
        # -----------------------------------------------------------------
        # Single tool result → use existing generate() (identical to before)
        # Multiple tool results → use generate_combined() for one coherent response
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
        # STEP 6: BUILD FINAL AGENT RESPONSE
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
        self._save_turn(context, user_input, final_response, classification, tool_reasoning=tool_reasoning)
        return final_response
    
    def _run_tool(
        self,
        classification: ClassificationResponse,
        context: AgentContext
    ):
        """
        Get the tool from registry and execute it. Returns structured data only.
        
        Called from the reflection loop in process_request().
        Does NOT generate NL or build AgentResponse — the loop handles that
        after all steps are complete.
        
        ARCHITECTURAL PATTERN:
        1. Tool returns STRUCTURED DATA (facts, confidence, reasoning)
        2. NL generation happens AFTER the reflection loop exits
        3. This keeps the loop focused on structured data only
        """
        print(f"[Orchestrator] Routing to: {classification.intent}")
        
        # Get tool instance from registry (injects llm_service, template_service)
        tool = self._registry.get(
            classification.intent,
            llm_service=self._llm,
            template_service=self._templates
        )
        
        # =================================================================
        # BUILD STRUCTURED REQUEST FOR TOOL
        # -----------------------------------------------------------------
        # PATTERN: Open/Closed Principle (SOLID)
        # 
        # Each tool knows how to build its own request from classification.
        # This eliminates the switch statement - tool owns its request type.
        # - Open for extension (add new tools freely)
        # - Closed for modification (orchestrator code unchanged)
        # =================================================================
        request = tool.build_request(classification)
        print(f"[Orchestrator] ✓ Built {type(request).__name__}: '{classification.rewritten_prompt[:50]}...'")
        
        # Execute the tool - returns STRUCTURED DATA (not NL)
        tool_response = tool.execute(request, context)
        
        print(f"[Orchestrator] ✓ Received structured response from {classification.intent}")
        print(f"[Orchestrator]   Response type: {type(tool_response).__name__}")
        
        return tool_response
    
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
        
        # =====================================================================
        # STEP 10: PROGRESSIVE SUMMARIZATION (fold old turns if window overflows)
        # ---------------------------------------------------------------------
        # SLIDING WINDOW + PROGRESSIVE SUMMARIZATION PATTERN:
        # When we have more turns than context_window_size, the oldest turn
        # outside the window gets "folded" into a compressed summary.
        #
        # EXAMPLE: context_window_size = 3
        #   Turn 9 arrives → fold turn 6 into summary → window = [7, 8, 9]
        #
        # The summary preserves key facts without sending full history to LLM.
        # Uses the same fast SLM as classification (cheap, fast, sufficient).
        # =====================================================================
        self._maybe_fold_oldest_turn(session_id)
    
    def _maybe_fold_oldest_turn(self, session_id: str) -> None:
        """
        Fold the oldest turn into the summary if window overflows.
        
        Called after every save_turn. Checks if total turns exceeds
        the context_window_size and folds the oldest turn if needed.
        
        SLIDING WINDOW PATTERN:
        - We keep exactly K turns in the sliding window
        - When turn K+1 arrives, turn 1 gets folded into summary
        - Summary is compressed text, not full conversation
        
        Uses ConversationSummarizer with the fast SLM (gpt-4.1-mini).
        """
        turn_count = self._memory.get_turn_count(session_id)
        window_size = settings.context_window_size
        
        # Only fold if we have more turns than the window allows
        if turn_count <= window_size:
            return
        
        print(f"[Orchestrator] Window overflow ({turn_count} > {window_size}) - folding oldest turn")
        
        # Get the oldest turn (will be removed after folding)
        oldest_turn = self._memory.pop_oldest_turn(session_id)
        if not oldest_turn:
            return
        
        # Get existing summary (may be empty for first fold)
        existing_summary = self._memory.get_summary(session_id)
        
        # Fold the turn into the summary using SLM
        updated_summary = self._summarizer.fold_turn(oldest_turn, existing_summary)
        
        # Save the updated summary
        self._memory.save_summary(session_id, updated_summary)
        
        print(f"[Orchestrator] ✓ Folded turn into summary, window now has {self._memory.get_turn_count(session_id)} turns")
