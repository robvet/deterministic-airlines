"""
Cancel Flight Tool - Handles flight cancellations.

This tool demonstrates:
1. Looking up existing bookings (grounding data)
2. Validating the booking exists
3. Simulating a cancellation operation
4. Returning structured response with refund info

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
                message=(
                    f"Could not find booking with confirmation '{request.confirmation_number}' "
                    f"or flight '{request.flight_number}'. Please verify your booking details."
                )
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
        # BREAKPOINT 5: VALIDATE AND RETURN RESPONSE
        # =================================================================
        response = CancelFlightResponse(
            success=True,
            confirmation_number=confirmation,
            refund_amount=refund_amount,
            message=(
                f"Successfully cancelled booking {confirmation} for {itinerary.get('passenger_name')}. "
                f"A refund of ${refund_amount:.2f} will be processed to your original payment method "
                f"within 5-7 business days."
            )
        )
        
        assert isinstance(response, CancelFlightResponse)
        print(f"[CancelFlightTool] ✓ Cancellation complete: {confirmation}, Refund: ${refund_amount}")
        
        return response
