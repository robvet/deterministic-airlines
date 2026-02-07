"""
Flight Status Tool - Checks flight status and disruption information.

This tool demonstrates:
1. Looking up flights from mock itinerary data
2. Checking for delays, cancellations, and connection impacts
3. Returning structured status information

SET BREAKPOINT in execute() to trace the full flow.
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
    
    def build_request(self, classification) -> FlightStatusRequest:
        """Build FlightStatusRequest from classification result."""
        entities = {e.type: e.value for e in classification.entities}
        return FlightStatusRequest(
            flight_number=entities.get("flight_number"),
            confirmation_number=entities.get("confirmation_number")
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
        # =================================================================
        segment = None
        itinerary = None
        scenario_key = None
        
        # Try confirmation number first
        if request.confirmation_number:
            itinerary = get_itinerary_by_confirmation(request.confirmation_number)
            if itinerary and itinerary.get("segments"):
                segment = itinerary["segments"][0]  # Get first segment
                print(f"[FlightStatusTool] Found itinerary by confirmation")
        
        # Try flight number
        if not segment and request.flight_number:
            result = get_itinerary_by_flight(request.flight_number)
            if result:
                scenario_key, itinerary = result
                # Find the specific segment
                for seg in itinerary.get("segments", []):
                    if seg.get("flight_number", "").upper() == request.flight_number.upper():
                        segment = seg
                        break
                print(f"[FlightStatusTool] Found flight in {scenario_key} itinerary")
        
        # =================================================================
        # BREAKPOINT 3: BUILD STATUS RESPONSE
        # =================================================================
        if not segment:
            print(f"[FlightStatusTool] Flight not found")
            return FlightStatusResponse(
                found=False,
                status_facts=[
                    f"Flight {request.flight_number or request.confirmation_number} not found in system"
                ],
                reasoning="No matching flight found in mock itinerary data"
            )
        
        # Build status facts
        status_facts = [
            f"Flight number: {segment.get('flight_number')}",
            f"Route: {segment.get('origin')} → {segment.get('destination')}",
            f"Status: {segment.get('status', 'On time')}",
            f"Departure: {segment.get('departure', 'TBD')}",
            f"Arrival: {segment.get('arrival', 'TBD')}",
            f"Gate: {segment.get('gate', 'TBD')}"
        ]
        
        # Check for connection impact (disrupted scenario)
        reasoning = f"Flight found by {'confirmation' if request.confirmation_number else 'flight number'}"
        if scenario_key == "disrupted" and segment.get("flight_number") == "PA441":
            status_facts.append("CONNECTION IMPACT: Delay will cause missed connection to flight NY802")
            status_facts.append("RECOMMENDATION: Rebooking is recommended")
            reasoning += ". Detected disrupted scenario - PA441 delay impacts NY802 connection."
        
        response = FlightStatusResponse(
            found=True,
            flight_number=segment.get("flight_number"),
            origin=segment.get("origin"),
            destination=segment.get("destination"),
            status=segment.get("status", "On time"),
            departure_time=segment.get("departure"),
            arrival_time=segment.get("arrival"),
            gate=segment.get("gate"),
            status_facts=status_facts,
            reasoning=reasoning
        )
        
        print(f"[FlightStatusTool] ✓ Status: {response.status}")
        return response
