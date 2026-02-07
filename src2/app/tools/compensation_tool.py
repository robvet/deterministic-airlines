"""
Compensation Tool - Handles compensation for flight disruptions.

This tool demonstrates:
1. Assessing disruption severity
2. Issuing appropriate vouchers (hotel, meal, transport)
3. Opening compensation cases with tracking

SET BREAKPOINT in execute() to trace the full flow.
"""
import random
import string

from ..models.context import AgentContext
from ..models.compensation import CompensationRequest, CompensationResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from data.booking_data import get_itinerary_by_confirmation, get_itinerary_by_flight, MOCK_ITINERARIES


class CompensationTool:
    """
    Handles compensation requests for flight disruptions.
    
    Issues vouchers and creates compensation cases based on
    the type and severity of disruption.
    """
    
    def build_request(self, classification) -> CompensationRequest:
        """Build CompensationRequest from classification result."""
        entities = {e.type: e.value for e in classification.entities}
        return CompensationRequest(
            question=classification.rewritten_prompt,
            confirmation_number=entities.get("confirmation_number"),
            flight_number=entities.get("flight_number"),
            reason=entities.get("reason")
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
        print(f"[CompensationTool] Initialized")
    
    def execute(self, request: CompensationRequest, context: AgentContext) -> CompensationResponse:
        """
        Process a compensation request.
        
        Args:
            request: Validated CompensationRequest with disruption details
            context: Shared conversation context
            
        Returns:
            Validated CompensationResponse with case and voucher details
            
        DEBUGGING:
            Set breakpoints to trace:
            - BREAKPOINT 1: Validate input
            - BREAKPOINT 2: Look up booking and assess disruption
            - BREAKPOINT 3: Determine compensation level
            - BREAKPOINT 4: Issue vouchers and create case
        """
        # =================================================================
        # BREAKPOINT 1: VALIDATE STRUCTURED INPUT
        # =================================================================
        assert isinstance(request, CompensationRequest), \
            f"Expected CompensationRequest, got {type(request)}"
        assert isinstance(context, AgentContext), \
            f"Expected AgentContext, got {type(context)}"
        print(f"[CompensationTool] ✓ Received CompensationRequest")
        print(f"[CompensationTool]   Confirmation: {request.confirmation_number}, Reason: {request.reason}")
        
        # =================================================================
        # BREAKPOINT 2: LOOK UP BOOKING AND ASSESS DISRUPTION
        # =================================================================
        itinerary = None
        disruption_level = "minor"  # minor, significant, severe
        
        # Try to find the booking
        if request.confirmation_number:
            itinerary = get_itinerary_by_confirmation(request.confirmation_number)
        elif request.flight_number:
            result = get_itinerary_by_flight(request.flight_number)
            if result:
                _, itinerary = result
        
        # Check for known disruption scenarios
        if itinerary:
            # Check if this is the disrupted itinerary
            is_disrupted = itinerary.get("confirmation_number") == "IR-D204"
            if is_disrupted:
                disruption_level = "severe"  # Missed connection scenario
                print(f"[CompensationTool] Found disrupted itinerary - severe")
            else:
                disruption_level = "minor"
                print(f"[CompensationTool] Found on-time itinerary - minor")
        else:
            # No booking found, but still process request based on reason
            reason = (request.reason or request.question).lower()
            if any(word in reason for word in ["missed", "cancelled", "cancel"]):
                disruption_level = "severe"
            elif any(word in reason for word in ["delay", "late", "hour"]):
                disruption_level = "significant"
            print(f"[CompensationTool] No booking found, inferred level: {disruption_level}")
        
        # =================================================================
        # BREAKPOINT 3: DETERMINE COMPENSATION LEVEL
        # =================================================================
        vouchers = []
        total_value = 0.0
        
        if disruption_level == "severe":
            # Severe: missed connection, cancellation
            vouchers = [
                "$180 hotel voucher (partner hotel near terminal)",
                "$60 meal credit",
                "$40 ground transport credit"
            ]
            total_value = 280.0
        elif disruption_level == "significant":
            # Significant: long delay (3+ hours)
            vouchers = [
                "$60 meal credit"
            ]
            total_value = 60.0
        else:
            # Minor: short delay or general request
            vouchers = [
                "Documented for customer service follow-up"
            ]
            total_value = 0.0
        
        # Add itinerary-specific vouchers if available
        if itinerary and itinerary.get("vouchers"):
            vouchers = list(itinerary["vouchers"].values())
            total_value = sum(
                float(v.split("$")[1].split()[0]) 
                for v in vouchers 
                if "$" in v
            ) if vouchers else 0.0
        
        print(f"[CompensationTool] Vouchers to issue: {len(vouchers)}, Total: ${total_value}")
        
        # =================================================================
        # BREAKPOINT 4: ISSUE VOUCHERS AND CREATE CASE
        # =================================================================
        case_id = "CMP-" + "".join(random.choices(string.digits, k=4))
        
        # Build structured facts and reasoning based on disruption level
        compensation_facts = [f"Case ID: {case_id}"]
        
        if disruption_level == "severe":
            compensation_facts.extend([
                "Disruption type: missed connection",
                "Entitled to overnight accommodations"
            ])
            for voucher in vouchers:
                compensation_facts.append(f"Voucher: {voucher}")
            compensation_facts.append(f"Total compensation value: ${total_value:.2f}")
            reasoning = "Severe disruption (missed connection) - full compensation package issued"
            next_steps = (
                "1. Check in to partner hotel using voucher. "
                "2. Use meal credit at airport restaurants. "
                "3. Rebooking confirmed for tomorrow morning. "
                "4. Save receipts for additional expenses."
            )
        elif disruption_level == "significant":
            compensation_facts.append("Disruption type: significant delay")
            for voucher in vouchers:
                compensation_facts.append(f"Voucher: {voucher}")
            compensation_facts.append("Vouchers valid at airport restaurants and shops")
            reasoning = "Significant delay - meal credit compensation issued"
            next_steps = "Use meal credit at any airport restaurant. Show case number."
        else:
            compensation_facts.extend([
                "Disruption type: minor",
                "Concern documented for follow-up",
                "Customer service will respond within 24 hours"
            ])
            reasoning = "Minor disruption - documentation only, no vouchers required"
            next_steps = "No immediate action needed. We'll be in touch."
        
        response = CompensationResponse(
            case_opened=True,
            case_id=case_id,
            vouchers=vouchers,
            total_value=total_value if total_value > 0 else None,
            compensation_facts=compensation_facts,
            reasoning=reasoning,
            next_steps=next_steps
        )
        
        print(f"[CompensationTool] ✓ Case opened: {case_id}")
        return response
