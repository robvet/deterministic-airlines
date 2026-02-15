"""Memory package - Short-term conversation memory with pluggable providers."""
from .imemory_store import IMemoryStore
from .models import ConversationTurn
from .providers.in_memory import InMemoryStore

# NOTE: ContextManager is NOT exported here to keep one-way dependencies.
# Import directly: from ..memory.context_manager import ContextManager

__all__ = ["IMemoryStore", "ConversationTurn", "InMemoryStore"]
