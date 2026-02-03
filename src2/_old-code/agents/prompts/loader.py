"""
Prompt template loader for agent instructions.

Prompts are stored as plain text files with {placeholder} syntax for variable substitution.
This decouples prompt content from Python code, making it easy for workshop attendees
to modify prompts without touching agent implementation.

Usage:
    from ..prompts.loader import load_prompt
    
    def my_agent_instructions(run_context, agent) -> str:
        return load_prompt("my_agent", {
            "customer_name": ctx.customer_name,
            "flight": ctx.flight_number,
        })
"""
from pathlib import Path
from typing import Any


PROMPTS_DIR = Path(__file__).parent


def load_prompt(agent_name: str, variables: dict[str, Any] | None = None) -> str:
    """
    Load a prompt template and substitute variables.
    
    Args:
        agent_name: Name of the agent (matches filename without .txt extension)
        variables: Dict of {placeholder: value} for substitution. 
                   Placeholders in template use {name} syntax.
    
    Returns:
        Formatted prompt string with all placeholders replaced.
        
    Raises:
        FileNotFoundError: If the prompt template file doesn't exist.
        
    Example:
        Template contains: "Hello {name}, your flight {flight} is ready."
        load_prompt("greeting", {"name": "John", "flight": "PA441"})
        Returns: "Hello John, your flight PA441 is ready."
    """
    template_path = PROMPTS_DIR / f"{agent_name}.txt"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {template_path}. "
            f"Available prompts: {list_available_prompts()}"
        )
    
    template = template_path.read_text(encoding="utf-8")
    
    if variables:
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
    
    return template


def list_available_prompts() -> list[str]:
    """List all available prompt template names (without .txt extension)."""
    return [p.stem for p in PROMPTS_DIR.glob("*.txt")]
