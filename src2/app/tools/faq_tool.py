"""
FAQ Tool - Extracts relevant facts from knowledge base using LLM reasoning.

This tool demonstrates:
1. Loading an external prompt template
2. Injecting grounding data (FAQ knowledge base)  
3. Making an LLM call with structured output
4. Returning STRUCTURED DATA (not natural language)

ARCHITECTURAL PATTERN:
  - This tool uses LLM to reason over grounded knowledge
  - It returns structured facts, NOT natural language
  - The Orchestrator is responsible for NL generation

SET BREAKPOINT in execute() to trace the full flow.
"""
from ..models.context import AgentContext
from ..models.faq import FAQRequest, FAQResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from data.faq_data import get_formatted_faq_data


class FAQTool:
    """
    Handles FAQ and policy questions.
    
    Uses an LLM to reason over a grounded knowledge base,
    ensuring answers are factual and consistent.
    """
    
    def build_request(self, classification) -> FAQRequest:
        """Build FAQRequest from classification result."""
        return FAQRequest(question=classification.rewritten_prompt)
    
    def __init__(self, llm_service: LLMService, template_service: PromptTemplateService):
        """
        Initialize with required services.
        
        Args:
            llm_service: For making LLM calls
            template_service: For loading prompt templates
        """
        self._llm = llm_service
        self._templates = template_service
        print(f"[FAQTool] Initialized")
    
    def execute(self, request: FAQRequest, context: AgentContext) -> FAQResponse:
        """
        Extract relevant facts from knowledge base using LLM reasoning.
        
        Args:
            request: Validated FAQRequest containing the user's question
            context: Shared conversation context
            
        Returns:
            Validated FAQResponse with structured facts (not NL answer)
            
        DEBUGGING: 
            Set breakpoints and step through to see:
            - BREAKPOINT 1: Validate structured input from caller
            - BREAKPOINT 2: Load grounding data (FAQ knowledge base)
            - BREAKPOINT 3: Assemble data for context window
            - BREAKPOINT 4-5: Build context window + LLM call
            - BREAKPOINT 6: Validate structured output before returning
        """
        # =================================================================
        # BREAKPOINT 1: RECEIVE + VALIDATE STRUCTURED INPUT FROM CALLER
        # -----------------------------------------------------------------
        # DETERMINISTIC PATTERN: Validate inputs at tool boundary.
        # Even though orchestrator validated, we validate again.
        # The tool should not trust its caller blindly.
        # =================================================================
        assert isinstance(request, FAQRequest), \
            f"Expected FAQRequest, got {type(request)}"
        assert request.question, "FAQRequest.question cannot be empty"
        assert isinstance(context, AgentContext), \
            f"Expected AgentContext, got {type(context)}"
        print(f"[FAQTool] ✓ Received valid FAQRequest: '{request.question[:50]}...'")
        
        # =================================================================
        # BREAKPOINT 2: LOAD GROUNDING DATA (FAQ KNOWLEDGE BASE)
        # -----------------------------------------------------------------
        # Fetch the FAQ knowledge base that will be injected into the prompt.
        # This is the "grounding" data - factual content the LLM must use.
        # Without grounding, the LLM would rely on training data (unreliable).
        # =================================================================
        grounding_data = get_formatted_faq_data()
        print(f"[FAQTool] Loaded grounding data ({len(grounding_data)} chars)")
        
        # =================================================================
        # BREAKPOINT 3: ASSEMBLE DATA FOR CONTEXT WINDOW
        # -----------------------------------------------------------------
        # Combine the pieces that will form the system prompt:
        #   - customer_name: for personalization
        #   - question: the user's (rewritten) question
        #   - faq_knowledge_base: grounding data for factual answers
        #
        # The template uses {placeholder} syntax. PromptTemplateService
        # replaces each placeholder with actual values.
        #
        # This is CONTEXT ENGINEERING: deciding what the model sees.
        # =================================================================
        prompt = self._templates.load("faq_prompt", {
            "customer_name": context.customer_name,
            "question": request.question,
            "faq_knowledge_base": grounding_data
        })
        print(f"[FAQTool] Built prompt ({len(prompt)} chars)")
        
        # =================================================================
        # BREAKPOINT 4-5: BUILD CONTEXT WINDOW + LLM CALL
        # -----------------------------------------------------------------
        # HERE we build the required parameters for the context window:
        #   - system_prompt: The prompt template with grounding data (knowledge)
        #   - user_message: The user's question
        #   - assistants: Model responses from prior turns (if any)
        #
        # The llm_service.complete() will build the actual context window based upon 
        # the parameters we pass to it.
        #        
        # This LLM call is a SIMPLE CASE of context engineering:
        #   - only prompts and a knowledge source
        #   - no memory items, flight info, booking history, etc
        # 
        # This defines WHAT the LLM sees. LLMService wraps it as:
        #   messages = [
        #       {"role": "system", "content": prompt},      <- the knowledge
        #       {"role": "user", "content": user_message}   <- the question
        #       Response_model: Instructs LLMService about the format with which to return the answer
        #   ]
        #
        # Then:
        #   4. Sends context window to Azure OpenAI
        #   5a. Receives raw JSON response
        #   5b. Parses JSON to dict
        #   5c. Validates against FAQResponse schema
        # =================================================================
        response = self._llm.complete(
            system_prompt=prompt,
            user_message=request.question,
            response_model=FAQResponse
        )
        
        # =================================================================
        # BREAKPOINT 6: VALIDATE STRUCTURED OUTPUT BEFORE RETURNING
        # -----------------------------------------------------------------
        # DETERMINISTIC PATTERN: Validate outputs before returning.
        # Even though LLMService validated the response, we verify
        # again at the tool boundary. Defense in depth.
        #
        # NOTE: We validate structured data (relevant_facts), not NL.
        # The Orchestrator will generate natural language from this.
        # =================================================================
        assert isinstance(response, FAQResponse), \
            f"Expected FAQResponse, got {type(response)}"
        assert response.relevant_facts, "FAQResponse.relevant_facts cannot be empty"
        assert len(response.relevant_facts) >= 1, "Must have at least one relevant fact"
        assert 0.0 <= response.confidence <= 1.0, \
            f"Confidence must be 0.0-1.0, got {response.confidence}"
        print(f"[FAQTool] ✓ Validated FAQResponse (structured data)")
        print(f"[FAQTool]   Facts: {response.relevant_facts[:2]}{'...' if len(response.relevant_facts) > 2 else ''}")
        print(f"[FAQTool]   Confidence: {response.confidence}, Source: {response.source_topic}")
        print(f"[FAQTool]   Reasoning: {response.reasoning[:80]}...")
        
        return response
