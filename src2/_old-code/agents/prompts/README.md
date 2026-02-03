# Prompts Package

This folder contains prompt templates for each agent. Templates use `{placeholder}` syntax for variable substitution.

## Files

| File | Agent | Variables |
|------|-------|-----------|
| `triage.txt` | Triage Agent | `RECOMMENDED_PROMPT_PREFIX` |
| `faq.txt` | FAQ Agent | `RECOMMENDED_PROMPT_PREFIX` |
| `seat_services.txt` | Seat & Special Services | `RECOMMENDED_PROMPT_PREFIX`, `confirmation`, `flight`, `seat` |
| `flight_info.txt` | Flight Information | `RECOMMENDED_PROMPT_PREFIX`, `confirmation`, `flight` |
| `booking.txt` | Booking & Cancellation | `RECOMMENDED_PROMPT_PREFIX`, `confirmation`, `flight` |
| `refund.txt` | Refunds & Compensation | `RECOMMENDED_PROMPT_PREFIX`, `confirmation`, `case_id` |

## Usage

```python
from ..prompts.loader import load_prompt
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

def my_agent_instructions(run_context, agent) -> str:
    ctx = run_context.context.state
    return load_prompt("seat_services", {
        "RECOMMENDED_PROMPT_PREFIX": RECOMMENDED_PROMPT_PREFIX,
        "confirmation": ctx.confirmation_number or "[unknown]",
        "flight": ctx.flight_number or "[unknown]",
        "seat": ctx.seat_number or "[unassigned]",
    })
```

## Workshop Exercise

To modify agent behavior:
1. Open the appropriate `.txt` file
2. Edit the instructions
3. Restart the server
4. Test the changed behavior

No Python knowledge required!
