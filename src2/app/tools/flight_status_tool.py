"""
Flight Status Tool - Checks flight status and disruption information.

This tool demonstrates:
1. Looking up flights from mock itinerary data
2. Checking for delays, cancellations, and connection impacts
3. Returning structured status information

SET BREAKPOINT in execute() to trace the full flow.

WORKSHOP EXERCISE:
Implement the execute() method to:
1. Look up the flight/booking in mock data
2. Build and return a FlightStatusResponse
"""
from ..models.context import AgentContext
from ..models.flight_status import FlightStatusRequest, FlightStatusResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from data.booking_data import get_itinerary_by_confirmation, get_itinerary_by_flight, MOCK_ITINERARIES


class FlightStatusTool:
    """
    Handles flight status inquiries.
    
    Looks up flight information from mock data and returns
    current status, delays, and connection impacts.
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
        print(f"[FlightStatusTool] Initialized")
    
    def execute(self, request: FlightStatusRequest, context: AgentContext) -> FlightStatusResponse:
        """
        Check the status of a flight.
        
        Args:
            request: Validated FlightStatusRequest with flight/confirmation number
            context: Shared conversation context
            
        Returns:
            Validated FlightStatusResponse with status information
            
        DEBUGGING:
            Set breakpoints to trace:
            - BREAKPOINT 1: Validate input
            - BREAKPOINT 2: Look up flight in mock data
            - BREAKPOINT 3: Build status response
        """
        # =================================================================
        # BREAKPOINT 1: VALIDATE STRUCTURED INPUT
        # =================================================================
        assert isinstance(request, FlightStatusRequest), \
            f"Expected FlightStatusRequest, got {type(request)}"
        assert isinstance(context, AgentContext), \
            f"Expected AgentContext, got {type(context)}"
        print(f"[FlightStatusTool] ✓ Received FlightStatusRequest")
        print(f"[FlightStatusTool]   Flight: {request.flight_number}, Conf: {request.confirmation_number}")
        
        # =================================================================
        # BREAKPOINT 2: LOOK UP FLIGHT IN MOCK DATA
        # -----------------------------------------------------------------
        # TODO: Implement flight lookup
        #
        # Available helper functions (from data.booking_data):
        #   get_itinerary_by_confirmation(confirmation_number) -> dict or None
        #   get_itinerary_by_flight(flight_number) -> tuple(scenario_key, itinerary) or None
        #
        # Itinerary structure:
        #   itinerary["segments"] = [
        #       {"flight_number": "PA441", "origin": "CDG", "destination": "JFK", 
        #        "status": "Delayed 3 hours", "gate": "B7", ...},
        #       ...
        #   ]
        #
        # Steps:
        #   1. Try lookup by confirmation_number first (if provided)
        #   2. If not found, try lookup by flight_number
        #   3. Find the matching segment in the itinerary
        # =================================================================
        segment = None
        itinerary = None
        scenario_key = None
        
        # TODO: Look up by confirmation number
        # if request.confirmation_number:
        #     ...
        
        # TODO: Look up by flight number  
        # if not segment and request.flight_number:
        #     ...
        
        # =================================================================
        # BREAKPOINT 3: BUILD STATUS RESPONSE
        # -----------------------------------------------------------------
        # TODO: Return appropriate FlightStatusResponse
        #
        # If segment NOT found, return:
        #   FlightStatusResponse(
        #       found=False,
        #       message="Flight not found..."
        #   )
        #
        # If segment found, return:
        #   FlightStatusResponse(
        #       found=True,
        #       flight_number=segment.get("flight_number"),
        #       origin=segment.get("origin"),
        #       destination=segment.get("destination"),
        #       status=segment.get("status", "On time"),
        #       departure_time=segment.get("departure"),
        #       arrival_time=segment.get("arrival"),
        #       gate=segment.get("gate"),
        #       message="..."  # Human-readable status message
        #   )
        #
        # BONUS: Check for connection impacts in disrupted scenarios
        # =================================================================
        
        # TODO: Replace this placeholder with your implementation
        return FlightStatusResponse(
            found=False,
            message=f"TODO: Implement flight status lookup for {request.flight_number or request.confirmation_number}"
        )

##########################################
# TODO: Register FlightStatusTool in app/api/routes.py
##########################################
