"""
Book Flight Tool - Handles new flight bookings.

This tool demonstrates:
1. Loading flight inventory (grounding data)
2. Making an LLM call to extract booking details
3. Simulating a booking operation
4. Returning structured response

SET BREAKPOINT in execute() to trace the full flow.
"""
import random
import string

from ..models.context import AgentContext
from ..models.booking import BookFlightRequest, BookFlightResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from data.booking_data import get_available_flights, get_formatted_available_flights


class BookFlightTool:
    """
    Handles booking new flights.
    
    Uses an LLM to understand booking intent and match against
    available flight inventory.
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
        print(f"[BookFlightTool] Initialized")
    
    def execute(self, request: BookFlightRequest, context: AgentContext) -> BookFlightResponse:
        """
        Book a new flight for the customer.
        
        Args:
            request: Validated BookFlightRequest with booking details
            context: Shared conversation context
            
        Returns:
            Validated BookFlightResponse with confirmation details
            
        DEBUGGING:
            Set breakpoints to trace:
            - BREAKPOINT 1: Validate structured input
            - BREAKPOINT 2: Load available flights (grounding data)
            - BREAKPOINT 3: Build prompt with flight inventory
            - BREAKPOINT 4: LLM call to confirm booking details
            - BREAKPOINT 5: Simulate booking and validate response
        """
        # =================================================================
        # BREAKPOINT 1: VALIDATE STRUCTURED INPUT
        # =================================================================
        assert isinstance(request, BookFlightRequest), \
            f"Expected BookFlightRequest, got {type(request)}"
        assert isinstance(context, AgentContext), \
            f"Expected AgentContext, got {type(context)}"
        print(f"[BookFlightTool] ✓ Received BookFlightRequest")
        print(f"[BookFlightTool]   Flight: {request.flight_number}, Dest: {request.destination}")
        
        # =================================================================
        # BREAKPOINT 2: LOAD AVAILABLE FLIGHTS (GROUNDING DATA)
        # -----------------------------------------------------------------
        # Fetch flight inventory that will constrain the LLM's options.
        # This prevents the LLM from inventing non-existent flights.
        # =================================================================
        available_flights = get_available_flights(
            origin=request.origin,
            destination=request.destination
        )
        flights_text = get_formatted_available_flights()
        print(f"[BookFlightTool] Loaded {len(available_flights)} available flights")
        
        # =================================================================
        # BREAKPOINT 3: BUILD PROMPT WITH FLIGHT INVENTORY
        # =================================================================
        prompt = self._templates.load("book_flight_prompt", {
            "customer_name": context.customer_name,
            "available_flights": flights_text,
            "requested_flight": request.flight_number or "not specified",
            "requested_origin": request.origin or "not specified",
            "requested_destination": request.destination or "not specified",
            "requested_date": request.date or "not specified",
        })
        print(f"[BookFlightTool] Built prompt ({len(prompt)} chars)")
        
        # =================================================================
        # BREAKPOINT 4: SIMULATE BOOKING
        # -----------------------------------------------------------------
        # In a real system, this would:
        # 1. Call LLM to extract/confirm booking details
        # 2. Call reservation API to create booking
        # 3. Process payment
        # 
        # For the demo, we simulate a successful booking.
        # =================================================================
        
        # Find the requested flight or pick first available
        selected_flight = None
        if request.flight_number:
            for flight in available_flights:
                if flight["flight_number"].upper() == request.flight_number.upper():
                    selected_flight = flight
                    break
        
        if not selected_flight and available_flights:
            selected_flight = available_flights[0]
        
        if not selected_flight:
            print(f"[BookFlightTool] No matching flights found")
            return BookFlightResponse(
                success=False,
                message="No available flights match your request. Please try different dates or destinations."
            )
        
        # =================================================================
        # BREAKPOINT 5: GENERATE CONFIRMATION
        # =================================================================
        confirmation = "DA-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        seat = f"{random.randint(1, 30)}{random.choice(['A', 'B', 'C', 'D', 'E', 'F'])}"
        
        response = BookFlightResponse(
            success=True,
            confirmation_number=confirmation,
            flight_number=selected_flight["flight_number"],
            seat_assignment=seat,
            message=(
                f"Successfully booked flight {selected_flight['flight_number']} "
                f"from {selected_flight['origin']} to {selected_flight['destination']}. "
                f"Departure: {selected_flight['departure']}. "
                f"Confirmation: {confirmation}. Seat: {seat}."
            )
        )
        
        # Validate output
        assert isinstance(response, BookFlightResponse)
        assert response.confirmation_number, "Confirmation number required for successful booking"
        print(f"[BookFlightTool] ✓ Booking complete: {confirmation}")
        
        return response
