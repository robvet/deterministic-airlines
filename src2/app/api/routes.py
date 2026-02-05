"""
API Routes for Deterministic Airlines Agent.

Simple REST endpoints that call the OrchestratorAgent.
Similar to a Controller in ASP.NET or Spring.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..agents.orchestrator import OrchestratorAgent
from ..config.llm_config import LLMConfig
from ..memory import InMemoryStore
from ..models.context import AgentContext
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from ..tools.faq_tool import FAQTool
from ..tools.book_flight_tool import BookFlightTool
from ..tools.cancel_flight_tool import CancelFlightTool
from ..tools.flight_status_tool import FlightStatusTool
from ..tools.baggage_tool import BaggageTool
from ..tools.seat_tool import SeatTool
from ..tools.compensation_tool import CompensationTool
from ..tools.tool_registry import ToolRegistry


# Request/Response models
class ChatRequest(BaseModel):
    """Incoming chat message."""
    message: str = Field(..., min_length=1, description="User message")
    customer_name: str = Field(default="Guest", description="Customer name for context")
    bypass_classification: bool = Field(default=False, description="Skip intent classification, call LLM directly")


class ChatResponse(BaseModel):
    """Agent response."""
    answer: str
    routed_to: str
    confidence: float
    rewritten_input: str
    entities: list[dict] = []


# Module-level singleton (created once on first request)
_orchestrator: OrchestratorAgent | None = None
_context: AgentContext | None = None


def get_orchestrator() -> OrchestratorAgent:
    """
    Dependency provider for OrchestratorAgent.
    Creates singleton on first call.
    """
    global _orchestrator
    if _orchestrator is None:
        # Wire up dependencies (same as main.py)
        config = LLMConfig()
        config.validate()
        
        llm_service = LLMService(config)
        template_service = PromptTemplateService()
        memory_store = InMemoryStore()
        
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
        # registry.register(
        #    # ToDo Register Flight Status tool 
        # )
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
        
        _orchestrator = OrchestratorAgent(
            registry=registry,
            llm_service=llm_service,
            template_service=template_service,
            memory_store=memory_store
        )
    return _orchestrator


def get_context() -> AgentContext:
    """Dependency provider for AgentContext."""
    global _context
    if _context is None:
        _context = AgentContext(customer_name="API User")
    return _context


# Create router
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
    context: AgentContext = Depends(get_context),
) -> ChatResponse:
    """
    Main Chat Endpoint - Process user messages through the agent pipeline.
    
    Request:
        POST /chat
        Body: {"message": "What is the baggage policy?", "customer_name": "John"}
    
    Response:
        {
            "answer": "...",
            "routed_to": "faq",
            "confidence": 0.95,
            "rewritten_input": "..."
        }
    """
    # Update context if customer name provided
    if request.customer_name != "Guest":
        context.customer_name = request.customer_name
    
    context.turn_count += 1
    
    # Call orchestrator
    response = orchestrator.handle(request.message, context, bypass_classification=request.bypass_classification)
    
    return ChatResponse(
        answer=response.answer,
        routed_to=response.routed_to,
        confidence=response.confidence,
        rewritten_input=response.rewritten_input,
        entities=[{"type": e.type, "value": e.value} for e in response.entities]
    )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check for infrastructure probes."""
    return {"status": "healthy"}
