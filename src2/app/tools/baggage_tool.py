"""
Baggage Tool - Handles baggage inquiries and lost bag claims.

=============================================================================
STRUCTURED DATA OUTPUT (NO NATURAL LANGUAGE)
=============================================================================

This tool demonstrates:
1. Policy-based responses for baggage allowance and fees
2. Filing lost bag claims with claim number generation
3. Simple pattern matching for inquiry type detection

ARCHITECTURAL PATTERN:
  - Tool returns STRUCTURED DATA (policy facts, reasoning, claim info)
  - Orchestrator generates NATURAL LANGUAGE from structured data
  - Single point of NL generation for consistency and control

SET BREAKPOINT in execute() to trace the full flow.
"""
import random
import string

from ..models.context import AgentContext
from ..models.baggage import BaggageRequest, BaggageResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService


# =============================================================================
# BAGGAGE POLICY DATA (Grounding)
# =============================================================================
BAGGAGE_POLICIES = {
    "allowance": {
        "carry_on": "One carry-on bag (22x14x9 inches) + one personal item",
        "checked_premium": "First checked bag free for premium members",
        "checked_economy": "$35 for first checked bag, $45 for second",
        "weight_limit": "50 lbs per checked bag"
    },
    "fees": {
        "overweight": "$75 for bags over 50 lbs",
        "oversized": "$100 for bags over 62 linear inches",
        "extra_bag": "$45 for third+ bags",
        "sports_equipment": "$35 per item"
    },
    "lost_bag": {
        "claim_window": "File within 24 hours of arrival",
        "delivery_promise": "Delivery within 5 business days",
        "interim_expenses": "Up to $50/day for essential items while bag is located"
    }
}


class BaggageTool:
    """
    Handles baggage-related inquiries.
    
    Answers questions about allowances, fees, and lost bag claims
    using grounded policy data.
    """
    
    def build_request(self, classification) -> BaggageRequest:
        """Build BaggageRequest from classification result."""
        entities = {e.type: e.value for e in classification.entities}
        return BaggageRequest(
            question=classification.rewritten_prompt,
            confirmation_number=entities.get("confirmation_number"),
            baggage_tag=entities.get("baggage_tag")
        )
    
    def __init__(self, llm_service: LLMService, template_service: PromptTemplateService):
        """
        Initialize with required services.
        
        Args:
            llm_service: For making LLM calls
            template_service: For loading prompt templates
        """
        self._llm = llm_service
        self._templates = template_service
        print(f"[BaggageTool] Initialized")
    
    def execute(self, request: BaggageRequest, context: AgentContext) -> BaggageResponse:
        """
        Handle a baggage inquiry.
        
        Args:
            request: Validated BaggageRequest with the inquiry details
            context: Shared conversation context
            
        Returns:
            Validated BaggageResponse with answer and any claim info
            
        DEBUGGING:
            Set breakpoints to trace:
            - BREAKPOINT 1: Validate input
            - BREAKPOINT 2: Detect inquiry type
            - BREAKPOINT 3: Build response from policy data
        """
        # =================================================================
        # BREAKPOINT 1: VALIDATE STRUCTURED INPUT
        # =================================================================
        assert isinstance(request, BaggageRequest), \
            f"Expected BaggageRequest, got {type(request)}"
        assert isinstance(context, AgentContext), \
            f"Expected AgentContext, got {type(context)}"
        print(f"[BaggageTool] ✓ Received BaggageRequest: '{request.question[:50]}...'")
        
        # =================================================================
        # BREAKPOINT 2: DETECT INQUIRY TYPE
        # -----------------------------------------------------------------
        # Simple keyword-based classification for demo purposes.
        # In production, the orchestrator's NER would handle this.
        # =================================================================
        query = request.question.lower()
        
        if any(word in query for word in ["lost", "missing", "can't find", "didn't arrive"]):
            category = "lost"
        elif any(word in query for word in ["fee", "cost", "charge", "price", "how much"]):
            category = "fees"
        elif any(word in query for word in ["allowance", "include", "how many", "limit", "weight"]):
            category = "allowance"
        else:
            category = "policy"
        
        print(f"[BaggageTool] Detected category: {category}")
        
        # =================================================================
        # BREAKPOINT 3: BUILD STRUCTURED RESPONSE FROM POLICY DATA
        # -----------------------------------------------------------------
        # Returns STRUCTURED DATA, not natural language.
        # Orchestrator will generate NL from these facts.
        # =================================================================
        claim_number = None
        tracking_url = None
        policy_facts = []
        reasoning = ""
        
        if category == "lost":
            # Generate a claim number for lost bag
            claim_number = "BG-" + "".join(random.choices(string.digits, k=6))
            tracking_url = f"https://deterministic.airlines/baggage/track/{claim_number}"
            policy_facts = [
                f"Claim number: {claim_number}",
                f"Claim window: {BAGGAGE_POLICIES['lost_bag']['claim_window']}",
                f"Delivery promise: {BAGGAGE_POLICIES['lost_bag']['delivery_promise']}",
                f"Interim expenses: {BAGGAGE_POLICIES['lost_bag']['interim_expenses']}",
                f"Tracking URL: {tracking_url}"
            ]
            reasoning = "User reported lost/missing bag - filed claim and provided tracking info"
            
        elif category == "fees":
            fees = BAGGAGE_POLICIES["fees"]
            policy_facts = [
                f"Overweight bags (>50 lbs): {fees['overweight']}",
                f"Oversized bags (>62 linear inches): {fees['oversized']}",
                f"Extra bags (3rd+): {fees['extra_bag']}",
                f"Sports equipment: {fees['sports_equipment']}"
            ]
            reasoning = "User asked about baggage fees - returning fee schedule from policy"
            
        elif category == "allowance":
            allowance = BAGGAGE_POLICIES["allowance"]
            policy_facts = [
                f"Carry-on: {allowance['carry_on']}",
                f"Premium checked: {allowance['checked_premium']}",
                f"Economy checked: {allowance['checked_economy']}",
                f"Weight limit: {allowance['weight_limit']}"
            ]
            reasoning = "User asked about baggage allowance - returning allowance limits from policy"
            
        else:
            # General policy overview
            policy_facts = [
                f"Carry-on allowance: {BAGGAGE_POLICIES['allowance']['carry_on']}",
                f"First checked bag (economy): {BAGGAGE_POLICIES['allowance']['checked_economy']}",
                f"Weight limit: {BAGGAGE_POLICIES['allowance']['weight_limit']}",
                "For lost bags, describe what happened and we'll file a claim"
            ]
            reasoning = "General baggage policy inquiry - providing overview of key policies"
        
        response = BaggageResponse(
            policy_facts=policy_facts,
            category=category,
            reasoning=reasoning,
            claim_number=claim_number,
            tracking_url=tracking_url
        )
        
        print(f"[BaggageTool] ✓ Structured response ready, category: {category}, facts: {len(policy_facts)}")
        return response
