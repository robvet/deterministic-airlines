"""
Simplified Single Agent for OpenAI Airlines.

This is a streamlined alternative to the multi-agent architecture.
One agent with all tools - no handoffs, no triage, no complexity.

Usage:
    from app.airline.agent import AirlineAgent
    
    agent = AirlineAgent()
    result = agent.run("Can you change my seat to 14C?")
"""
from typing import Any, List

from agents import Agent, Runner, ItemHelpers

from ..tools import (
    faq_lookup_tool,
    flight_status_tool,
    get_matching_flights,
    get_trip_details,
    book_new_flight,
    cancel_flight,
    update_seat,
    assign_special_service_seat,
    display_seat_map,
    issue_compensation,
    baggage_tool,
)
from ..context import AirlineAgentContext


class SimpleContextWrapper:
    """
    Minimal context wrapper that mimics the ChatKit structure.
    Tools expect: context.context.state
    """
    
    def __init__(self, state: AirlineAgentContext):
        self.state = state


class AgentResult:
    """Result container from running the agent."""
    
    def __init__(self, response: str, new_items: List[Any], raw_result: Any):
        self._response = response
        self._new_items = new_items
        self._raw_result = raw_result
    
    @property
    def response(self) -> str:
        """The agent's text response."""
        return self._response
    
    @property
    def new_items(self) -> List[Any]:
        """New items produced by the agent run."""
        return self._new_items
    
    @property
    def raw_result(self) -> Any:
        """The raw RunResult from the SDK."""
        return self._raw_result
    
    def __str__(self) -> str:
        return self._response
    
    def __repr__(self) -> str:
        return f"AgentResult(response='{self._response[:50]}...')"


class AirlineAgent:
    """
    Simplified single-agent for airline customer service.
    
    One agent with all tools - no handoffs, no triage, no complexity.
    Perfect for training, demos, and debugging.
    
    Usage:
        agent = AirlineAgent()
        result = agent.run("Change my seat to 14C")
        print(result.response)
    """
    
    INSTRUCTIONS = """
You are an airline customer service agent. You help customers with:

- **Flight Information**: Check flight status, find flights, get trip details
- **Bookings**: Book new flights, cancel existing bookings
- **Seats**: Change seats, request special service seats, show seat maps
- **Baggage**: Track bags, file claims, answer baggage policy questions
- **Compensation**: Issue refunds, vouchers, and travel credits
- **FAQs**: Answer common questions about policies

## Customer Context
When a customer provides their confirmation number, use it for all relevant operations.
The customer's current booking info (if available):
- Confirmation: {confirmation_number}
- Flight: {flight_number}  
- Seat: {seat_number}
- Passenger: {passenger_name}

## Guidelines
1. Be helpful, concise, and professional
2. Use tools to look up information - don't guess
3. Confirm actions before making changes (cancellations, seat changes)
4. If you can't help with something, say so clearly
"""

    TOOLS = [
        faq_lookup_tool,
        flight_status_tool,
        get_matching_flights,
        get_trip_details,
        book_new_flight,
        cancel_flight,
        update_seat,
        assign_special_service_seat,
        display_seat_map,
        issue_compensation,
        baggage_tool,
    ]

    def __init__(self, context: AirlineAgentContext | None = None):
        """
        Initialize the airline agent.
        
        Args:
            context: Customer context with booking info (optional)
        """
        self._context = context if context else self._create_default_context()
        self._input_items: List[dict[str, Any]] = []
        self._agent: Agent = self._build_agent()
    
    @staticmethod
    def _create_default_context() -> AirlineAgentContext:
        """Create default customer context."""
        return AirlineAgentContext(
            passenger_name="John Smith",
            confirmation_number="IR-D204",
            seat_number="12A",
            flight_number="DA789",
        )
    
    @property
    def context(self) -> AirlineAgentContext:
        """Current customer context."""
        return self._context
    
    @context.setter
    def context(self, value: AirlineAgentContext) -> None:
        """Update customer context and rebuild agent with new instructions."""
        self._context = value
        self._agent = self._build_agent()
    
    @property
    def input_items(self) -> List[dict[str, Any]]:
        """Conversation history."""
        return self._input_items
    
    @property
    def agent_name(self) -> str:
        """Name of the underlying agent."""
        return self._agent.name
    
    def _build_agent(self) -> Agent:
        """Build the Agent instance with current context injected into instructions."""
        instructions = self.INSTRUCTIONS.format(
            confirmation_number=self._context.confirmation_number or "Not provided",
            flight_number=self._context.flight_number or "Not provided",
            seat_number=self._context.seat_number or "Not provided",
            passenger_name=self._context.passenger_name or "Not provided",
        )
        return Agent(
            name="Airline Agent",
            instructions=instructions,
            tools=self.TOOLS,
        )
    
    def run(self, user_input: str) -> AgentResult:
        """
        Run the agent with user input.
        
        Args:
            user_input: The user's message
            
        Returns:
            AgentResult with response text and metadata
        """
        self._input_items.append({"role": "user", "content": user_input})
        
        # Wrap context for tools (they expect context.context.state)
        context_wrapper = SimpleContextWrapper(self._context)
        
        result = Runner.run_sync(
            self._agent,
            self._input_items,
            context=context_wrapper,
        )
        
        response_text = self._extract_response(result.new_items)
        self._input_items = result.to_input_list()
        
        return AgentResult(
            response=response_text,
            new_items=result.new_items,
            raw_result=result,
        )
    
    def _extract_response(self, items: List[Any]) -> str:
        """Extract text response from agent output items."""
        response_parts = []
        for item in items:
            text = ItemHelpers.text_message_output(item)
            if text:
                response_parts.append(text)
        return "".join(response_parts)
    
    def reset(self) -> None:
        """Reset conversation history."""
        self._input_items = []
    
    def __repr__(self) -> str:
        return f"AirlineAgent(context={self._context.confirmation_number})"
