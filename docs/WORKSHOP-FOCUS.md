# Workshop Focus Guide

This document identifies the **teaching folders** for the OpenAI Airlines workshop on deterministic AI engineering.

The following table presents critical touchpoints that demonstrate deterministic touchpoints. 

## Deterministic Validation Breakpoints

| # | File | Location | What It Shows |
|---|------|----------|---------------|
| **1** | `intent_classifier.py` | `classify()` ~L48 | LLM call to build ClassificationResponse |
| **2** | `intent_classifier.py` | `classify()` ~L55 | Validate ClassificationResponse before returning to orchestrator |
| **3** | `orchestrator.py` | `handle()` ~L92 | Receive + validate ClassificationResponse from intent classifier |
| **4** | `orchestrator.py` | `_execute_tool()` ~L162 | Build FAQRequest structured object |
| **5** | `orchestrator.py` | `_execute_tool()` ~L172 | Validate FAQRequest before sending to tool |
| **6** | `faq_tool.py` | `execute()` ~L48 | Receive + validate FAQRequest at tool entry |
| **7** | `faq_tool.py` | `execute()` ~L60 | Build context window (load grounding data) |
| **8** | `faq_tool.py` | `execute()` ~L70 | Populate prompt template with variables |
| **9** | `llm_service.py` | `complete()` ~L78 | LLM API call (inspect prompt, model selection) |
| **10a** | `llm_service.py` | `complete()` ~L90 | Raw LLM response (JSON string from model) |
| **10b** | `llm_service.py` | `complete()` ~L97 | JSON parsing (string → dict) |
| **10c** | `llm_service.py` | `complete()` ~L107 | Pydantic validation (dict → validated model) |
| **11** | `faq_tool.py` | `execute()` ~L95 | Validate FAQResponse before returning to orchestrator |
| **12** | `orchestrator.py` | `_execute_tool()` ~L182 | Receive + validate FAQResponse from tool |
| **13** | `orchestrator.py` | `_execute_tool()` ~L195 | Build AgentResponse, return to user |

### Key Pattern: Validate at Every Boundary














## TL;DR - Where to Focus

| Folder | Purpose | Workshop Relevance |
|--------|---------|-------------------|
| `src/app/airline/orchestrator.py` | **Debug entry point** | **CRITICAL** - Set breakpoint here to trace flow |
| `src/app/airline/prompts/` | Prompt templates | **HIGH** - Prompt engineering exercises |
| `src/app/airline/tools/` | Agent tools (functions) | **HIGH** - Structured I/O, function calling |
| `src/app/airline/agents/` | Agent definitions | **HIGH** - Orchestration, handoffs, guardrails |
| `src/app/airline/guardrails.py` | Input validation | **MEDIUM** - Safety patterns |
| `src/app/airline/context.py` | Context DTOs | **MEDIUM** - Context management |
| `src/app/server.py` | Infrastructure | **LOW** - Plumbing, stay out |

---

## Orchestrator (`src/app/airline/orchestrator.py`)

**What it teaches:** Agent execution pipeline, debugging entry point

**THIS IS WHERE YOU SET YOUR BREAKPOINT** to step through the entire agent flow:

```python
# orchestrator.py - Line ~85
async def run_conversation(agent, input_items, context):
    # >>> BREAKPOINT HERE <<<
    result = Runner.run_streamed(agent, input_items, context=context)
    ...
```

**Debug Session Flow:**
1. Set breakpoint at `run_conversation()` 
2. Send message: "change my seat"
3. Step through:
   - Triage agent receives message
   - Triage decides → handoff to Seat Agent
   - Handoff callback hydrates context
   - Seat Agent calls `display_seat_map` tool
   - Response streams back
4. Continue → plumbing handles WebSocket (invisible)

**Key objects to watch in debugger:**
- `result.new_items` - Handoffs, tool calls, messages
- `result.last_agent.name` - Currently active agent
- `context.state` - Customer data (flight, seat, confirmation)

**Why this file exists:** Isolates orchestration from WebSocket/HTTP plumbing in `server.py`. Developers debug here; they never touch `server.py`.

---

## Prompts (`src/app/airline/prompts/`)

**What it teaches:** Prompt engineering, instruction tuning, context injection

```
prompts/
├── loader.py          # Template loading utility
├── triage.txt         # Orchestrator agent instructions
├── faq.txt            # FAQ agent instructions
├── seat_services.txt  # Seat agent instructions
├── flight_info.txt    # Flight agent instructions
├── booking.txt        # Booking agent instructions
└── refund.txt         # Refunds agent instructions
```

**Exercises:**
1. Open any `.txt` file and modify the instructions
2. Restart server to see behavior changes
3. No Python knowledge required for basic prompt tuning

**Key concept:** Templates use `{placeholder}` syntax for dynamic values (confirmation number, flight number, etc.)

---

## Tools (`src/app/airline/tools/`)

**What it teaches:** Structured I/O, Pydantic validation, function calling

```
tools/
├── __init__.py            # Re-exports all tools
├── faq_tools.py           # faq_lookup_tool
├── flight_tools.py        # flight_status_tool, get_matching_flights, get_trip_details
├── booking_tools.py       # book_new_flight, cancel_flight
├── seat_tools.py          # update_seat, assign_special_service_seat, display_seat_map
├── compensation_tools.py  # issue_compensation
└── baggage_tools.py       # baggage_tool (orphaned - exercise!)
```

**Exercises:**
1. Examine tool function signatures with `@function_tool` decorator
2. Note Pydantic models for input validation
3. Add new tool parameter (e.g., `meal_preference` to booking)
4. **Exercise:** Wire `baggage_tool` to a new Baggage Agent

**Key concept:** Each tool is a function the LLM can call. Pydantic ensures inputs are validated.

---

## Agents (`src/app/airline/agents/`)

**What it teaches:** Agent orchestration, handoffs, guardrails

```
agents/
├── __init__.py             # Handoff wiring (late-binding pattern)
├── handoff_callbacks.py    # Context hydration on handoff
├── triage_agent.py         # Orchestrator - routes to specialists
├── faq_agent.py            # Policy questions
├── seat_agent.py           # Seat changes, accessibility
├── flight_agent.py         # Flight status, delays
├── booking_agent.py        # Bookings, cancellations
└── refund_agent.py         # Compensation, vouchers
```

**Exercises:**
1. Trace handoff flow in `__init__.py` - see how agents connect
2. Examine guardrail attachment in each agent file
3. Study `handoff_callbacks.py` - context hydration before handoff
4. **Exercise:** Add a new Baggage Agent following the existing pattern

**Key concepts:**
- **Late-binding pattern:** Agents created with empty handoffs, wired later to avoid circular imports
- **Guardrails:** `jailbreak_guardrail`, `relevance_guardrail` attached to each agent
- **Handoff callbacks:** Ensure context is populated before agent receives control

---

## Guardrails (`src/app/airline/guardrails.py`)

**What it teaches:** Input validation, safety patterns

**Key patterns:**
- `jailbreak_guardrail` - Blocks prompt injection attempts
- `relevance_guardrail` - Ensures on-topic requests

**Order matters:** Jailbreak check runs first (security), then relevance check.

---

## Context (`src/app/airline/context.py`)

**What it teaches:** Context management, state DTOs

**Contains:**
- `AirlineAgentChatContext` - Per-conversation state
- Fields: confirmation_number, flight_number, seat_number, etc.

**Key concept:** Context flows through the agent pipeline, hydrated by handoff callbacks.

---

## Files to Ignore

These files are infrastructure plumbing - developers don't need to modify them:

| File | Purpose | Why Ignore |
|------|---------|------------|
| `server.py` | WebSocket/event broadcasting | Infrastructure |
| `main.py` | FastAPI app setup | Boilerplate |
| `azure_client.py` | Azure OpenAI client | Config only |
| `memory_store.py` | Thread memory | Infrastructure |
| `api/routes.py` | HTTP endpoints | ChatKit handles this |
| `run.py` | Entry point | Just starts server |

---

## Quick Reference: What Goes Where

| When you want to... | Edit this file... |
|---------------------|-------------------|
| **Debug the entire agent flow** | `orchestrator.py` (set breakpoint at `run_conversation()`) |
| Change how an agent responds | `prompts/<agent>.txt` |
| Add a new tool | `tools/<domain>_tools.py` + `tools/__init__.py` |
| Create a new agent | `agents/<name>_agent.py` + `agents/__init__.py` |
| Change handoff behavior | `agents/__init__.py` (handoff wiring) |
| Modify context hydration | `agents/handoff_callbacks.py` |
| Add a guardrail | `guardrails.py` + attach in agent files |
| Add context field | `context.py` |

---

## Architecture Overview

```
User Message
     │
     │  (server.py - plumbing, ignore)
     │
     ▼
┌────────────────────────────────────────────┐
│  orchestrator.py - BREAKPOINT HERE      │
│  run_conversation()                     │
└──────────────────────┬─────────────────────┘
                       │
                       ▼
              ┌─────────────┐
              │  Guardrails │ ◄── jailbreak, relevance
              └─────┬───────┘
                    │
                    ▼
              ┌─────────────┐
              │   Triage    │ ◄── Routes by intent
              │   Agent     │
              └─────┬───────┘
                    │ Handoff
                    ▼
              ┌─────────────┐
              │ Specialist  │ ◄── FAQ, Seat, Flight, Booking, Refund
              │   Agent     │
              └─────┬───────┘
                    │ Tool Calls
                    ▼
              ┌─────────────┐
              │    Tools    │ ◄── lookup, update, book, cancel
              └─────────────┘
```

---

## Next Steps

1. **Start with prompts/** - Lowest friction, immediate feedback
2. **Explore tools/** - Understand structured I/O
3. **Study agents/** - Learn orchestration patterns
4. **Exercise:** Build a Baggage Agent end-to-end
