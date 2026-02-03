"""
Tool Registry - Discovery pattern for orchestration routing.

Each tool registers with:
  - name: unique identifier (e.g., "faq", "booking")
  - description: what the tool handles (used by LLM to route)
  - tool_class: the actual tool class to instantiate

The orchestrator uses get_routing_descriptions() to build its prompt,
then get() to retrieve the selected tool instance.
"""

from dataclasses import dataclass
from typing import Dict, Type, Any


@dataclass
class ToolInfo:
    """Metadata about a registered tool."""
    name: str
    description: str
    tool_class: Type[Any]


class ToolRegistry:
    """
    Registry for tool discovery and routing.
    
    Usage:
        registry = ToolRegistry()
        registry.register("faq", "Answers general questions...", FAQTool)
        registry.register("booking", "Handles reservations...", BookingTool)
        
        # Get descriptions for LLM routing prompt
        descriptions = registry.get_routing_descriptions()
        
        # After LLM selects a tool, get the instance
        tool = registry.get("faq")
        result = tool.execute(request, context)
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolInfo] = {}
        print(f"[ToolRegistry] Initialized")
    
    def register(self, name: str, description: str, tool_class: Type[Any]) -> None:
        """
        Register a tool for discovery.
        
        Args:
            name: Unique identifier (e.g., "faq", "booking")
            description: What this tool handles - used by LLM for routing
            tool_class: The tool class to instantiate when selected
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")
        
        self._tools[name] = ToolInfo(
            name=name,
            description=description,
            tool_class=tool_class
        )
        print(f"[ToolRegistry] Registered tool: {name}")
    
    def get(self, name: str, **kwargs) -> Any:
        """
        Get a tool instance by name.
        
        Args:
            name: The tool identifier
            **kwargs: Constructor arguments to pass to the tool class
            
        Returns:
            Instantiated tool object
            
        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            available = list(self._tools.keys())
            raise KeyError(f"Tool '{name}' not found. Available: {available}")
        
        tool_info = self._tools[name]
        # Instantiate the tool class with provided arguments
        return tool_info.tool_class(**kwargs)
    
    def get_routing_descriptions(self) -> str:
        """
        Get formatted tool descriptions for LLM routing prompt.
        
        Returns:
            Multi-line string like:
            "- faq: Answers general questions about baggage...
             - booking: Handles flight reservations..."
        """
        lines = []
        for name, info in self._tools.items():
            lines.append(f"- {name}: {info.description}")
        
        return "\n".join(lines)
    
    def list_tools(self) -> list[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
