"""
Deterministic Airlines Agent - Entry Point

This is the main entry point for the workshop demo.
All dependencies are wired up explicitly here - no hidden magic.

TO DEBUG:
1. Set a breakpoint on line "response = orchestrator.process_request(...)"
2. Run with debugger (F5 in VS Code)
3. Step into (F11) to trace the full flow

WORKSHOP OBJECTIVES DEMONSTRATED:
1. Tool Discovery - See ToolRegistry.register() and get()
2. Intent Classification - See IntentClassifier with NER and prompt rewriting
3. Prompt Engineering - See prompts/intent_prompt.txt and prompts/faq_prompt.txt
4. Context Management - See AgentContext passed through the pipeline
5. Structured I/O - See Pydantic models at every step
"""
from app.agents.orchestrator import OrchestratorAgent
from app.config.llm_config import LLMConfig
from app.memory import InMemoryStore
from app.models.context import AgentContext
from app.services.llm_service import LLMService
from app.services.prompt_template_service import PromptTemplateService
from app.tools.faq_tool import FAQTool
from app.tools.book_flight_tool import BookFlightTool
from app.tools.cancel_flight_tool import CancelFlightTool
from app.tools.flight_status_tool import FlightStatusTool
from app.tools.baggage_tool import BaggageTool
from app.tools.seat_tool import SeatTool
from app.tools.compensation_tool import CompensationTool
from app.tools.tool_registry import ToolRegistry


def main():
    """
    Main entry point - wires dependencies and runs REPL.
    """
    # Load and validate configuration
    print("Loading configuration...")
    config = LLMConfig()
    config.validate()
    print(f"Execution model: {config.azure_deployment}")
    print(f"Classifier model: {config.classifier_deployment}")
    
    # Create core services
    llm_service = LLMService(config)
    template_service = PromptTemplateService()
    memory_store = InMemoryStore()
    
    # Register tools (discovery pattern)
    registry = ToolRegistry()
    registry.register(
        name="faq",
        description="Answers general questions about baggage, policies, fees, and airline procedures",
        tool_class=FAQTool
    )
    registry.register(
        name="book_flight",
        description="Books a new flight reservation for the customer",
        tool_class=BookFlightTool
    )
    registry.register(
        name="cancel_flight",
        description="Cancels an existing flight booking and processes refunds",
        tool_class=CancelFlightTool
    )
    registry.register(
        name="flight_status",
        description="Checks the status of a flight including delays, cancellations, and gate information",
        tool_class=FlightStatusTool
    )
    registry.register(
        name="baggage",
        description="Handles baggage inquiries including allowance, fees, and lost bag claims",
        tool_class=BaggageTool
    )
    registry.register(
        name="seat",
        description="Handles seat selection, changes, and special service seating requests",
        tool_class=SeatTool
    )
    registry.register(
        name="compensation",
        description="Processes compensation requests for delays, cancellations, and missed connections",
        tool_class=CompensationTool
    )
    
    # Create orchestrator
    orchestrator = OrchestratorAgent(
        registry=registry,
        llm_service=llm_service,
        template_service=template_service,
        memory_store=memory_store
    )
    
    # Show registered tools
    print("\n--- Registered Tools ---")
    print(registry.get_routing_descriptions())
    
    # Create conversation context
    context = AgentContext(customer_name="Workshop Attendee")
    
    # Run REPL loop
    print("\n" + "=" * 60)
    print("Deterministic Airlines Agent")
    print("Ask any question (baggage, wifi, seats, booking, etc.)")
    print("Type 'exit' to quit")
    print("=" * 60 + "\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
            
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
        
        context.turn_count += 1
        
        # SET BREAKPOINT HERE - Step into (F11) to trace the full flow
        response = orchestrator.process_request(user_input, context)
        
        print(f"\nAgent: {response.answer}")
        print(f"       [routed: {response.routed_to}, confidence: {response.confidence:.2f}]")
        print(f"       [rewritten: {response.rewritten_input}]\n")


if __name__ == "__main__":
    main()
