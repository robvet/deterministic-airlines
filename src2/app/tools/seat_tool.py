"""
Seat Tool - Handles seat selection and special service requests.

This tool demonstrates:
1. Seat assignment and changes
2. Special service accommodation (medical, wheelchair)
3. Seat preference handling (window, aisle, front)

SET BREAKPOINT in execute() to trace the full flow.
"""
import random
import string

from ..models.context import AgentContext
from ..models.seat import SeatRequest, SeatResponse
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from data.booking_data import get_itinerary_by_confirmation


# =============================================================================
# MOCK SEAT MAP (Grounding Data)
# =============================================================================
SEAT_MAP = {
    "front_row": ["1A", "1B", "1C", "1D", "1E", "1F"],
    "exit_row": ["14A", "14B", "14C", "14D", "14E", "14F"],
    "window": [f"{row}A" for row in range(1, 31)] + [f"{row}F" for row in range(1, 31)],
    "aisle": [f"{row}C" for row in range(1, 31)] + [f"{row}D" for row in range(1, 31)],
    "taken": ["1B", "2A", "14C", "14D", "23A", "23B"]  # Already assigned seats
}


class SeatTool:
    """
    Handles seat selection and special service requests.
    
    Assigns seats based on preferences and accommodates
    special needs with priority seating.
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
        print(f"[SeatTool] Initialized")
    
    def execute(self, request: SeatRequest, context: AgentContext) -> SeatResponse:
        """
        Handle a seat selection or change request.
        
        Args:
            request: Validated SeatRequest with seat preferences
            context: Shared conversation context
            
        Returns:
            Validated SeatResponse with assignment result
            
        DEBUGGING:
            Set breakpoints to trace:
            - BREAKPOINT 1: Validate input
            - BREAKPOINT 2: Check current seat (if changing)
            - BREAKPOINT 3: Find best available seat
            - BREAKPOINT 4: Assign seat and build response
        """
        # =================================================================
        # BREAKPOINT 1: VALIDATE STRUCTURED INPUT
        # =================================================================
        assert isinstance(request, SeatRequest), \
            f"Expected SeatRequest, got {type(request)}"
        assert isinstance(context, AgentContext), \
            f"Expected AgentContext, got {type(context)}"
        print(f"[SeatTool] ✓ Received SeatRequest: '{request.question[:50]}...'")
        
        # =================================================================
        # BREAKPOINT 2: CHECK CURRENT SEAT (IF CHANGING)
        # =================================================================
        previous_seat = None
        if request.confirmation_number:
            itinerary = get_itinerary_by_confirmation(request.confirmation_number)
            if itinerary:
                previous_seat = itinerary.get("seat_number")
                print(f"[SeatTool] Current seat: {previous_seat}")
        
        # =================================================================
        # BREAKPOINT 3: FIND BEST AVAILABLE SEAT
        # =================================================================
        selected_seat = None
        special_service_noted = False
        
        # Handle special needs with priority
        if request.special_needs:
            # Special needs get front row priority
            for seat in SEAT_MAP["front_row"]:
                if seat not in SEAT_MAP["taken"]:
                    selected_seat = seat
                    special_service_noted = True
                    print(f"[SeatTool] Special needs: assigned front row {seat}")
                    break
        
        # Handle specific seat request
        elif request.requested_seat:
            seat = request.requested_seat.upper()
            if seat not in SEAT_MAP["taken"]:
                selected_seat = seat
                print(f"[SeatTool] Assigned requested seat: {seat}")
            else:
                print(f"[SeatTool] Requested seat {seat} is taken")
        
        # Handle preference (window, aisle, front)
        elif request.preference:
            pref = request.preference.lower()
            if "window" in pref:
                candidates = SEAT_MAP["window"]
            elif "aisle" in pref:
                candidates = SEAT_MAP["aisle"]
            elif "front" in pref:
                candidates = SEAT_MAP["front_row"]
            elif "exit" in pref:
                candidates = SEAT_MAP["exit_row"]
            else:
                candidates = [f"{row}B" for row in range(1, 31)]  # Middle seats
            
            for seat in candidates:
                if seat not in SEAT_MAP["taken"]:
                    selected_seat = seat
                    print(f"[SeatTool] Preference '{pref}': assigned {seat}")
                    break
        
        # Default: assign any available seat
        if not selected_seat:
            for row in range(5, 25):
                for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                    seat = f"{row}{col}"
                    if seat not in SEAT_MAP["taken"]:
                        selected_seat = seat
                        break
                if selected_seat:
                    break
            print(f"[SeatTool] Default assignment: {selected_seat}")
        
        # =================================================================
        # BREAKPOINT 4: BUILD RESPONSE
        # =================================================================
        if not selected_seat:
            return SeatResponse(
                success=False,
                message="Unable to find an available seat matching your preferences. "
                        "Please contact customer service for assistance."
            )
        
        # Build success message
        if special_service_noted:
            message = (
                f"Special service seat {selected_seat} has been assigned. "
                f"Your special needs request has been noted on the booking. "
                "A crew member will assist you during boarding."
            )
        elif previous_seat:
            message = (
                f"Your seat has been changed from {previous_seat} to {selected_seat}. "
                "Your boarding pass will be updated."
            )
        else:
            message = (
                f"Seat {selected_seat} has been assigned to your booking. "
                "Check your boarding pass for details."
            )
        
        response = SeatResponse(
            success=True,
            seat_number=selected_seat,
            previous_seat=previous_seat,
            message=message,
            special_service_noted=special_service_noted
        )
        
        print(f"[SeatTool] ✓ Assigned seat: {selected_seat}")
        return response
