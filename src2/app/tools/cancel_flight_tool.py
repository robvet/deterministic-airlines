"""
Cancel Flight Tool - Handles flight cancellations.

=============================================================================
STRUCTURED DATA OUTPUT (NO NATURAL LANGUAGE)
=============================================================================

This tool demonstrates:
1. Looking up existing bookings (grounding data)
2. Validating the booking exists
3. Simulating a cancellation operation
4. Returning structured response with refund info

ARCHITECTURAL PATTERN:
  - Tool returns STRUCTURED DATA (cancellation facts, reasoning)
  - Orchestrator generates NATURAL LANGUAGE from structured data
  - Single point of NL generation for consistency and control

SET BREAKPOINT in execute() to trace the full flow.
"""
from ..models.context import AgentContext
from ..models.booking import CancelFlightRequest, CancelFlightResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from data.booking_data import get_itinerary_by_confirmation, get_itinerary_by_flight


class CancelFlightTool:
    """
    Handles cancellation of existing bookings.
    
    Validates the booking exists before processing cancellation.
    """
    
    def build_request(self, classification) -> CancelFlightRequest:
        """Build CancelFlightRequest from classification result."""
        entities = {e.type: e.value for e in classification.entities}
        return CancelFlightRequest(
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
        print(f"[CancelFlightTool] Initialized")
    
    def execute(self, request: CancelFlightRequest, context: AgentContext) -> CancelFlightResponse:
        """
        Cancel an existing flight booking.
        
        Args:
            request: Validated CancelFlightRequest with booking identifier
            context: Shared conversation context
            
        Returns:
            Validated CancelFlightResponse with cancellation details
            
        DEBUGGING:
            Set breakpoints to trace:
            - BREAKPOINT 1: Validate structured input
            - BREAKPOINT 2: Look up booking (grounding data)
            - BREAKPOINT 3: Validate booking exists
            - BREAKPOINT 4: Process cancellation and calculate refund
            - BREAKPOINT 5: Validate and return response
        """
        # =================================================================
        # BREAKPOINT 1: VALIDATE STRUCTURED INPUT
        # =================================================================
        assert isinstance(request, CancelFlightRequest), \
            f"Expected CancelFlightRequest, got {type(request)}"
        assert isinstance(context, AgentContext), \
            f"Expected AgentContext, got {type(context)}"
        print(f"[CancelFlightTool] ✓ Received CancelFlightRequest")
        print(f"[CancelFlightTool]   Confirmation: {request.confirmation_number}, Flight: {request.flight_number}")
        
        # =================================================================
        # BREAKPOINT 2: LOOK UP BOOKING (GROUNDING DATA)
        # -----------------------------------------------------------------
        # Find the booking using confirmation number or flight number.
        # Try both fields since user might provide either.
        # This ensures we only cancel bookings that actually exist.
        # =================================================================
        itinerary = None
        confirmation = request.confirmation_number
        
        # Try confirmation number first
        if confirmation:
            itinerary = get_itinerary_by_confirmation(confirmation)
        
        # Try flight number as confirmation (user might say "cancel IR-D204")
        if not itinerary and request.flight_number:
            itinerary = get_itinerary_by_confirmation(request.flight_number)
            if itinerary:
                confirmation = request.flight_number
        
        # Try flight number as actual flight
        if not itinerary and request.flight_number:
            result = get_itinerary_by_flight(request.flight_number)
            if result:
                _, itinerary = result
                confirmation = itinerary.get("confirmation_number")
        
        # =================================================================
        # BREAKPOINT 3: VALIDATE BOOKING EXISTS
        # =================================================================
        if not itinerary:
            print(f"[CancelFlightTool] Booking not found")
            return CancelFlightResponse(
                success=False,
                cancellation_facts=[
                    f"Booking not found",
                    f"Searched confirmation: {request.confirmation_number or 'not provided'}",
                    f"Searched flight: {request.flight_number or 'not provided'}"
                ],
                reasoning="Could not locate booking in system - verify confirmation number or flight number"
            )
        
        print(f"[CancelFlightTool] Found booking: {confirmation}")
        print(f"[CancelFlightTool]   Passenger: {itinerary.get('passenger_name')}")
        
        # =================================================================
        # BREAKPOINT 4: PROCESS CANCELLATION AND CALCULATE REFUND
        # -----------------------------------------------------------------
        # In a real system, this would:
        # 1. Check cancellation policy
        # 2. Calculate refund based on time to departure
        # 3. Process refund to original payment method
        # 4. Update reservation system
        # 
        # For the demo, we simulate a successful cancellation with refund.
        # =================================================================
        
        # Simulate refund calculation (in reality, based on fare rules)
        refund_amount = 250.00  # Mock refund
        
        # =================================================================
        # BREAKPOINT 5: BUILD STRUCTURED RESPONSE
        # -----------------------------------------------------------------
        # Returns STRUCTURED DATA, not natural language.
        # Orchestrator will generate NL from these facts.
        # =================================================================
        cancellation_facts = [
            f"Booking cancelled: {confirmation}",
            f"Passenger: {itinerary.get('passenger_name')}",
            f"Refund amount: ${refund_amount:.2f}",
            "Refund timeline: 5-7 business days to original payment method"
        ]
        
        response = CancelFlightResponse(
            success=True,
            cancellation_facts=cancellation_facts,
            reasoning=f"Successfully cancelled booking {confirmation} and initiated refund",
            confirmation_number=confirmation,
            refund_amount=refund_amount
        )
        
        assert isinstance(response, CancelFlightResponse)
        print(f"[CancelFlightTool] ✓ Cancellation complete: {confirmation}, facts: {len(cancellation_facts)}")
        
        return response
