# Refactoring Plan: OpenAI Airlines Demo

## Overview
This document captures the complete refactoring strategy for transforming the OpenAI Airlines reference app from a monolithic proof-of-concept into an enterprise-grade, workshop-ready codebase.

## Goal
Transform monolithic OpenAI reference app into enterprise-grade structure for workshop use.

## Workshop Objectives
Enable training on deterministic engineering:
1. **Prompt Engineering** - Tune prompts in isolated files
2. **Context Management** - Explicit context window control
3. **Structured I/O** - Pydantic models for tool inputs/outputs
4. **Reflection Agent** - Add self-evaluation agent (future exercise)

---

## Architecture Overview

### Current Stack
- **Python 3.11** with FastAPI backend on port 8000
- **OpenAI Agents SDK** (`openai-agents` package): Orchestration framework with Agent, Runner, Handoff, Tool, Guardrail components
- **OpenAI ChatKit** (`openai-chatkit` package): UI/transport layer - handles HTTP routing, SSE streaming, thread management between React UI and Python backend
- **Azure OpenAI**: Backend LLM via `AsyncAzureOpenAI` client with `set_default_openai_client()`
- **React/Next.js UI** in `src/ui/` on port 3000

### Current Agent Architecture
6 specialized agents with handoff pattern:
- **Triage Agent** - Orchestrator, routes to specialists
- **FAQ Agent** - Policy questions using faq_lookup_tool
- **Seat & Special Services Agent** - Seat changes, medical/accessibility needs
- **Flight Information Agent** - Status, delays, connection risks
- **Booking & Cancellation Agent** - New bookings, rebookings, cancellations
- **Refunds & Compensation Agent** - Vouchers, cases after disruptions

### Handoff Flow
```
User → Triage → [Specialist Agent] → (may handoff to another) → Triage
                     ↓
              Can call tools
```

---

## Phase 1: Tools Extraction ✅ READY

### Current State
`airline/tools.py` - 320 lines, 11 tools all in one file

### Target Structure
```
airline/tools/
  __init__.py           # Re-exports all tools for backward compatibility
  faq_tools.py          # faq_lookup_tool
  flight_tools.py       # flight_status_tool, get_matching_flights, get_trip_details
  booking_tools.py      # book_new_flight, cancel_flight
  seat_tools.py         # update_seat, assign_special_service_seat, display_seat_map
  compensation_tools.py # issue_compensation
  baggage_tools.py      # baggage_tool (currently orphaned - workshop exercise)
```

### Tool-to-File Mapping

| Tool | Target File | Used By Agents |
|------|-------------|----------------|
| `faq_lookup_tool` | `faq_tools.py` | FAQ, Refunds |
| `flight_status_tool` | `flight_tools.py` | Flight Info |
| `get_matching_flights` | `flight_tools.py` | Flight Info, Booking |
| `get_trip_details` | `flight_tools.py` | Triage |
| `book_new_flight` | `booking_tools.py` | Booking |
| `cancel_flight` | `booking_tools.py` | Booking |
| `update_seat` | `seat_tools.py` | Seat Services |
| `assign_special_service_seat` | `seat_tools.py` | Seat Services |
| `display_seat_map` | `seat_tools.py` | Seat Services |
| `issue_compensation` | `compensation_tools.py` | Refunds |
| `baggage_tool` | `baggage_tools.py` | NONE (orphaned) |

### Shared Dependencies
All tools need:
```python
from agents import RunContextWrapper, function_tool
from chatkit.types import ProgressUpdateEvent
from ..context import AirlineAgentChatContext
from ..demo_data import apply_itinerary_defaults, active_itinerary, get_itinerary_for_flight
```

### __init__.py Pattern
```python
"""
Tools package - Domain-organized agent tools.

Tools are shared resources that can be used by multiple agents.
Each module groups related functionality by business domain.
"""

# FAQ domain
from .faq_tools import faq_lookup_tool

# Flight domain
from .flight_tools import flight_status_tool, get_matching_flights, get_trip_details

# Booking domain
from .booking_tools import book_new_flight, cancel_flight

# Seat domain
from .seat_tools import update_seat, assign_special_service_seat, display_seat_map

# Compensation domain
from .compensation_tools import issue_compensation

# Baggage domain (no agent yet - workshop exercise)
from .baggage_tools import baggage_tool

__all__ = [
    # FAQ
    "faq_lookup_tool",
    # Flight
    "flight_status_tool",
    "get_matching_flights", 
    "get_trip_details",
    # Booking
    "book_new_flight",
    "cancel_flight",
    # Seat
    "update_seat",
    "assign_special_service_seat",
    "display_seat_map",
    # Compensation
    "issue_compensation",
    # Baggage
    "baggage_tool",
]
```

### After Phase 1, Update agents.py Import
Change from:
```python
from .tools import (
    assign_special_service_seat,
    book_new_flight,
    ...
)
```
To:
```python
from .tools import (
    assign_special_service_seat,
    book_new_flight,
    ...
)
# Same import works because __init__.py re-exports everything
```

### Test
```bash
cd src
python -m uvicorn app.main:app --reload
# Test: Ask about flight status, book a flight, change seat
```

---

## Phase 2: Prompts Extraction

### Current State
Prompts are embedded as Python strings/functions in `agents.py`:
- 4 agents use dynamic instruction functions (inject context variables)
- 2 agents use static f-strings

### Target Structure
```
airline/prompts/
  triage.txt
  faq.txt
  seat_services.txt
  flight_info.txt
  booking.txt
  refund.txt
```

### Prompt Template Pattern
Use Jinja2-style placeholders for dynamic values:

**seat_services.txt:**
```
{RECOMMENDED_PROMPT_PREFIX}
You are the Seat & Special Services Agent. Handle seat changes and medical/special service requests.

1. The customer's confirmation number is {confirmation} for flight {flight} and current seat {seat}. 
   If any of these are missing, ask to confirm. If present, act without re-asking. Record any special needs.

2. Offer to open the seat map or capture a specific seat. Use assign_special_service_seat for front row/medical requests, 
   or update_seat for standard changes. If they want to choose visually, call display_seat_map.

3. Confirm the new seat and remind the customer it is saved on their confirmation.

Important: if the request is clear and data is present, perform multiple tool calls in a single turn without waiting for user replies. 
When done, emit at most one handoff: to Refunds & Compensation if disruption support is pending, to Baggage if baggage help is pending, otherwise back to Triage.

If the request is unrelated to seats or special services, transfer back to the Triage Agent.
```

### Prompt Loader Utility
Create `airline/prompts/loader.py`:
```python
"""Prompt template loader for agent instructions."""
from pathlib import Path
from typing import Dict, Any

PROMPTS_DIR = Path(__file__).parent

def load_prompt(agent_name: str, variables: Dict[str, Any] | None = None) -> str:
    """
    Load a prompt template and optionally substitute variables.
    
    Args:
        agent_name: Name of the agent (matches filename without .txt)
        variables: Dict of {placeholder: value} for substitution
    
    Returns:
        Formatted prompt string
    """
    template_path = PROMPTS_DIR / f"{agent_name}.txt"
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    
    template = template_path.read_text(encoding="utf-8")
    
    if variables:
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
    
    return template
```

### Updated Agent Instruction Function Pattern
```python
from ..prompts.loader import load_prompt
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

def seat_services_instructions(
    run_context: RunContextWrapper[AirlineAgentChatContext], 
    agent: Agent[AirlineAgentChatContext]
) -> str:
    ctx = run_context.context.state
    return load_prompt("seat_services", {
        "RECOMMENDED_PROMPT_PREFIX": RECOMMENDED_PROMPT_PREFIX,
        "confirmation": ctx.confirmation_number or "[unknown]",
        "flight": ctx.flight_number or "[unknown]",
        "seat": ctx.seat_number or "[unassigned]",
    })
```

### Workshop Benefit
Attendees can:
1. Open `prompts/seat_services.txt` in any text editor
2. Modify prompt wording, add/remove instructions
3. Restart server to see changes
4. No Python knowledge required for prompt tuning

### Test
```bash
cd src
python -m uvicorn app.main:app --reload
# Test: Each agent should respond with updated prompt behavior
```

---

## Phase 3: Agents Extraction

### Current State
`airline/agents.py` - 220 lines, 6 agents + 5 instruction functions + 2 handoff callbacks + handoff wiring

### Target Structure
```
airline/agents/
  __init__.py           # Handoff wiring (late-binding pattern) + re-exports
  base.py               # Shared agent utilities (if needed)
  triage_agent.py
  faq_agent.py
  seat_agent.py
  flight_agent.py
  booking_agent.py
  refund_agent.py
  handoff_callbacks.py  # on_seat_booking_handoff, on_booking_handoff
```

### Critical: Late-Binding Pattern for Handoffs

**Problem:** Circular imports
```python
# triage_agent.py
from .faq_agent import faq_agent  # faq_agent imports triage_agent for handoff back!
```

**Solution:** Create agents WITHOUT handoffs, wire in `__init__.py`

**Individual agent file pattern (seat_agent.py):**
```python
"""Seat & Special Services Agent - handles seat changes and accessibility requests."""
from agents import Agent, RunContextWrapper

from ...azure_client import MODEL
from ..context import AirlineAgentChatContext
from ..guardrails import jailbreak_guardrail, relevance_guardrail
from ..tools import update_seat, assign_special_service_seat, display_seat_map
from ..prompts.loader import load_prompt
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


def seat_services_instructions(
    run_context: RunContextWrapper[AirlineAgentChatContext], 
    agent: Agent[AirlineAgentChatContext]
) -> str:
    """Dynamic instructions with context injection."""
    ctx = run_context.context.state
    return load_prompt("seat_services", {
        "RECOMMENDED_PROMPT_PREFIX": RECOMMENDED_PROMPT_PREFIX,
        "confirmation": ctx.confirmation_number or "[unknown]",
        "flight": ctx.flight_number or "[unknown]",
        "seat": ctx.seat_number or "[unassigned]",
    })


# Create agent WITHOUT handoffs - wired in __init__.py
seat_special_services_agent = Agent[AirlineAgentChatContext](
    name="Seat and Special Services Agent",
    model=MODEL,
    handoff_description="Updates seats and handles medical or special service seating.",
    instructions=seat_services_instructions,
    tools=[update_seat, assign_special_service_seat, display_seat_map],
    input_guardrails=[relevance_guardrail, jailbreak_guardrail],
    handoffs=[],  # Empty! Wired later.
)
```

**__init__.py - Handoff Wiring:**
```python
"""
Agents package - Specialized airline customer service agents.

IMPORTANT: Handoffs are wired here to avoid circular imports.
Individual agent files create agents with empty handoffs lists.
"""
from agents import handoff

# Import all agents
from .triage_agent import triage_agent
from .faq_agent import faq_agent
from .seat_agent import seat_special_services_agent
from .flight_agent import flight_information_agent
from .booking_agent import booking_cancellation_agent
from .refund_agent import refunds_compensation_agent

# Import handoff callbacks
from .handoff_callbacks import on_seat_booking_handoff, on_booking_handoff

# === HANDOFF WIRING ===
# This runs at import time, after all agents are created

triage_agent.handoffs = [
    flight_information_agent,
    handoff(agent=booking_cancellation_agent, on_handoff=on_booking_handoff),
    handoff(agent=seat_special_services_agent, on_handoff=on_seat_booking_handoff),
    faq_agent,
    refunds_compensation_agent,
]

faq_agent.handoffs.append(triage_agent)

seat_special_services_agent.handoffs.extend([refunds_compensation_agent, triage_agent])

flight_information_agent.handoffs.extend([
    handoff(agent=booking_cancellation_agent, on_handoff=on_booking_handoff),
    triage_agent,
])

booking_cancellation_agent.handoffs.extend([
    handoff(agent=seat_special_services_agent, on_handoff=on_seat_booking_handoff),
    refunds_compensation_agent,
    triage_agent,
])

refunds_compensation_agent.handoffs.extend([faq_agent, triage_agent])

# Re-export for external use
__all__ = [
    "triage_agent",
    "faq_agent", 
    "seat_special_services_agent",
    "flight_information_agent",
    "booking_cancellation_agent",
    "refunds_compensation_agent",
]
```

### handoff_callbacks.py
```python
"""Handoff callback functions for context hydration."""
import random
import string

from agents import RunContextWrapper
from ..context import AirlineAgentChatContext
from ..demo_data import apply_itinerary_defaults


async def on_seat_booking_handoff(context: RunContextWrapper[AirlineAgentChatContext]) -> None:
    """Ensure context is hydrated when handing off to the seat and special services agent."""
    apply_itinerary_defaults(context.context.state)
    if context.context.state.flight_number is None:
        context.context.state.flight_number = f"FLT-{random.randint(100, 999)}"
    if context.context.state.confirmation_number is None:
        context.context.state.confirmation_number = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )


async def on_booking_handoff(context: RunContextWrapper[AirlineAgentChatContext]) -> None:
    """Prepare context when handing off to booking and cancellation."""
    apply_itinerary_defaults(context.context.state)
    if context.context.state.confirmation_number is None:
        context.context.state.confirmation_number = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
    if context.context.state.flight_number is None:
        context.context.state.flight_number = f"FLT-{random.randint(100, 999)}"
```

### Update server.py Import
Change from:
```python
from .airline.agents import triage_agent
```
To:
```python
from .airline.agents import triage_agent
# Same import works because __init__.py re-exports
```

### Test Matrix
| Test | Expected |
|------|----------|
| Triage → FAQ → Triage | ✅ Handoff works both ways |
| Triage → Seat → Refunds → Triage | ✅ Multi-hop handoff chain |
| Triage → Flight → Booking → Seat → Triage | ✅ Complex flow |
| Triage → Booking → Triage | ✅ Direct return |

---

## Phase 4: Server Refactoring

### Current State
`server.py` - ~420 lines containing:
- `AirlineServer` class (god class)
- `AgentEvent` dataclass
- `GuardrailCheck` dataclass
- `ConversationState` dataclass
- `_record_events()` async function
- `_record_guardrails()` async function
- Multiple helper methods mixed in class

### Target Structure
```
app/
  models/
    __init__.py
    events.py             # AgentEvent, GuardrailCheck dataclasses
    state.py              # ConversationState dataclass
  
  services/
    __init__.py
    agent_registry.py     # Agent initialization, get triage agent
    event_recorder.py     # Event recording logic
    guardrail_service.py  # Guardrail orchestration
  
  helpers/
    __init__.py
    message_utils.py      # Message formatting utilities
  
  server.py               # Thin AirlineServer (~100 lines)
```

### models/events.py
```python
"""Event and check models for agent execution tracking."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentEvent:
    """Represents an event during agent execution."""
    event_type: str
    agent: str | None = None
    content: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: str | None = None
    source_agent: str | None = None
    target_agent: str | None = None


@dataclass
class GuardrailCheck:
    """Represents a guardrail check result."""
    name: str
    triggered: bool
    message: str | None = None
```

### models/state.py
```python
"""Conversation state tracking."""
from dataclasses import dataclass, field


@dataclass
class ConversationState:
    """Tracks the state of a conversation for UI display."""
    events: list = field(default_factory=list)
    guardrail_checks: list = field(default_factory=list)
    current_agent: str | None = None
    context_snapshot: dict = field(default_factory=dict)
```

### services/event_recorder.py
```python
"""Event recording service for agent execution tracking."""
from typing import AsyncIterator
from agents import Agent
from agents.types import RunEvent

from ..models.events import AgentEvent


async def record_events(
    stream: AsyncIterator[RunEvent],
    state: "ConversationState",
) -> AsyncIterator[RunEvent]:
    """
    Wrap an event stream to record events for debugging/display.
    
    Yields events unchanged while capturing them in state.
    """
    async for event in stream:
        # Extract event info and append to state.events
        agent_event = _parse_run_event(event)
        if agent_event:
            state.events.append(agent_event)
        yield event


def _parse_run_event(event: RunEvent) -> AgentEvent | None:
    """Parse a RunEvent into an AgentEvent for display."""
    # Implementation extracts event_type, agent, content, etc.
    ...
```

### Thin server.py Pattern
```python
"""
Airline Demo Server - Thin orchestration layer.

Delegates to:
- services/event_recorder.py for event tracking
- services/guardrail_service.py for guardrail checks
- airline/agents/ for agent definitions
"""
from chatkit import ChatServer

from .models.state import ConversationState
from .services.event_recorder import record_events
from .services.guardrail_service import check_guardrails
from .airline.agents import triage_agent
from .airline.context import AirlineAgentChatContext


class AirlineServer(ChatServer[AirlineAgentChatContext]):
    """Airline customer service chat server."""
    
    def __init__(self):
        super().__init__(
            starting_agent=triage_agent,
            context_class=AirlineAgentChatContext,
        )
        self._conversation_states: dict[str, ConversationState] = {}
    
    async def run_with_tracking(self, thread_id: str, message: str):
        """Run agent with event and guardrail tracking."""
        state = self._get_or_create_state(thread_id)
        
        # Guardrail pre-check
        await check_guardrails(message, state)
        
        # Run agent with event recording
        async for event in record_events(self._run_agent(message), state):
            yield event
    
    def _get_or_create_state(self, thread_id: str) -> ConversationState:
        if thread_id not in self._conversation_states:
            self._conversation_states[thread_id] = ConversationState()
        return self._conversation_states[thread_id]
```

### Test
```bash
cd src
python -m uvicorn app.main:app --reload
# Test: Full conversation flow with UI showing events and guardrails
```

---

## File Inventory (Current State)

| File | Lines | Status | Phase |
|------|-------|--------|-------|
| `airline/tools.py` | ~320 | 🟡 11 tools in one file | Phase 1 |
| `airline/agents.py` | ~220 | 🟡 6 agents crammed together | Phase 3 |
| `server.py` | ~420 | 🔴 God class - mixed concerns | Phase 4 |
| `airline/context.py` | ~50 | 🟢 Clean - just DTOs | Done |
| `api/routes.py` | ~150 | 🟢 Clean - endpoint docs done | Done |
| `config/config.py` | ~30 | 🟢 Clean - centralized config | Done |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports | HIGH | HIGH | Late-binding pattern for handoffs in `__init__.py` |
| Handoff order breaks | MEDIUM | HIGH | Test each agent handoff individually after Phase 3 |
| Import path changes | MEDIUM | LOW | Update `__init__.py` re-exports maintain backward compat |
| Prompt template errors | LOW | MEDIUM | Add validation in prompt loader |
| Context not hydrated | LOW | MEDIUM | Handoff callbacks ensure context ready |

---

## Workshop Exercises (Future)

### Exercise 1: Prompt Engineering
**Objective:** Improve agent response quality through prompt tuning
1. Open `prompts/seat_services.txt`
2. Add instruction: "Always confirm the passenger's name before making changes"
3. Test conversation flow
4. Observe behavior change

### Exercise 2: Add Baggage Agent
**Objective:** Create a new agent using the established pattern
1. Create `agents/baggage_agent.py` following existing pattern
2. Create `prompts/baggage.txt`
3. Note: `baggage_tool` already exists in `tools/baggage_tools.py`
4. Add handoffs in `agents/__init__.py`
5. Update triage prompt to route baggage requests

### Exercise 3: Structured I/O
**Objective:** Add Pydantic models for tool inputs/outputs
1. Create `schemas/` folder
2. Define `SeatUpdateRequest`, `SeatUpdateResponse`
3. Update `update_seat` tool to use schemas
4. Observe improved error handling

### Exercise 4: Context Management
**Objective:** Implement explicit context window tracking
1. Create `services/context_manager.py`
2. Track token counts per message
3. Implement summarization when approaching limit
4. Display token usage in UI

### Exercise 5: Reflection Agent
**Objective:** Add self-evaluation loop
1. Create `agents/reflection_agent.py`
2. After each specialist response, reflection agent evaluates quality
3. If quality < threshold, request improvement
4. Limit reflection loops to prevent infinite recursion

---

## Architecture Diagrams

### Request Flow
```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────────┐
│ Next.js │────▶│ ChatKit  │────▶│ AirlineServer│────▶│ Triage Agent │
│   UI    │◀────│ (SSE)    │◀────│   (FastAPI)  │◀────│ → Specialist │
└─────────┘     └──────────┘     └─────────────┘     └──────────────┘
   :3000          Transport          :8000              OpenAI SDK
```

### Agent Handoff Graph
```
                    ┌─────────┐
                    │ Triage  │
                    └────┬────┘
         ┌───────┬───────┼───────┬───────┐
         ▼       ▼       ▼       ▼       ▼
      ┌─────┐ ┌──────┐ ┌─────┐ ┌─────┐ ┌─────┐
      │ FAQ │ │Flight│ │Seat │ │Book │ │Refund│
      └──┬──┘ └──┬───┘ └──┬──┘ └──┬──┘ └──┬──┘
         │       │        │       │       │
         └───────┴────────┴───────┴───────┘
                         │
                    Back to Triage
```

### Folder Structure (After All Phases)
```
src/app/
├── __init__.py
├── main.py                 # FastAPI app setup
├── server.py               # Thin AirlineServer
├── azure_client.py         # Azure OpenAI client
├── memory_store.py         # Thread memory
│
├── api/
│   ├── __init__.py
│   └── routes.py           # API endpoints
│
├── config/
│   ├── __init__.py
│   └── config.py           # Pydantic Settings
│
├── models/
│   ├── __init__.py
│   ├── events.py           # AgentEvent, GuardrailCheck
│   └── state.py            # ConversationState
│
├── services/
│   ├── __init__.py
│   ├── event_recorder.py
│   ├── guardrail_service.py
│   └── context_manager.py  # Future: token tracking
│
├── helpers/
│   ├── __init__.py
│   └── message_utils.py
│
└── airline/
    ├── __init__.py
    ├── context.py          # AirlineAgentChatContext
    ├── demo_data.py        # Mock itineraries
    ├── guardrails.py       # Input guardrails
    │
    ├── tools/
    │   ├── __init__.py     # Re-exports all
    │   ├── faq_tools.py
    │   ├── flight_tools.py
    │   ├── booking_tools.py
    │   ├── seat_tools.py
    │   ├── compensation_tools.py
    │   └── baggage_tools.py
    │
    ├── agents/
    │   ├── __init__.py     # Handoff wiring
    │   ├── triage_agent.py
    │   ├── faq_agent.py
    │   ├── seat_agent.py
    │   ├── flight_agent.py
    │   ├── booking_agent.py
    │   ├── refund_agent.py
    │   └── handoff_callbacks.py
    │
    └── prompts/
        ├── loader.py       # Template loader
        ├── triage.txt
        ├── faq.txt
        ├── seat_services.txt
        ├── flight_info.txt
        ├── booking.txt
        └── refund.txt
```

---

## Execution Checklist

### Phase 1: Tools ✅ COMPLETE
- [x] Create `airline/tools/` folder
- [x] Create `airline/tools/__init__.py`
- [x] Create `airline/tools/faq_tools.py`
- [x] Create `airline/tools/flight_tools.py`
- [x] Create `airline/tools/booking_tools.py`
- [x] Create `airline/tools/seat_tools.py`
- [x] Create `airline/tools/compensation_tools.py`
- [x] Create `airline/tools/baggage_tools.py`
- [x] Update `agents.py` import (should work unchanged due to re-exports)
- [x] Delete old `airline/tools.py`
- [x] Test: Start server, test tool calls

### Phase 2: Prompts ✅ COMPLETE
- [x] Create `airline/prompts/` folder
- [x] Create `airline/prompts/loader.py`
- [x] Create all 6 prompt template files
- [x] Update agent instruction functions to use loader
- [x] Test: Start server, verify agent responses

### Phase 3: Agents ✅ COMPLETE
- [x] Create `airline/agents/` folder
- [x] Create `airline/agents/handoff_callbacks.py`
- [x] Create all 6 agent files (with empty handoffs)
- [x] Create `airline/agents/__init__.py` with handoff wiring
- [x] Update `server.py` import (no change needed - re-exports work)
- [x] Delete old `airline/agents.py`
- [x] Test: All handoff paths verified

### Phase 4: Server ⏸️ FUTURE/OPTIONAL
> **Decision:** Deferred. Phases 1-3 deliver all workshop-relevant material.  
> Server.py is infrastructure plumbing (WebSockets, event broadcasting, state management).  
> Developers learning deterministic AI patterns should focus on prompts/, tools/, agents/.

- [ ] Create `models/` folder with events.py, state.py
- [ ] Create `services/` folder with recorder, guardrail service
- [ ] Create `helpers/` folder
- [ ] Refactor `server.py` to thin orchestrator
- [ ] Test: Full integration

---

## Notes & Discoveries
- `baggage_tool` exists in tools.py but no Baggage Agent - perfect workshop exercise
- ChatKit handles all HTTP/SSE transport - we don't touch that
- OpenAI Agents SDK provides orchestration (Agent, Runner, Handoff, Tool, Guardrail)
- Azure OpenAI backend via `AsyncAzureOpenAI` client with `set_default_openai_client()`
- `RECOMMENDED_PROMPT_PREFIX` from `agents.extensions.handoff_prompt` - standard handoff instructions
- Guardrails: `relevance_guardrail` and `jailbreak_guardrail` in `guardrails.py`
- Mock data in `demo_data.py` - provides disrupted/on_time itinerary scenarios
