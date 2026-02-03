"""
Memory Store Interface - Contract for pluggable memory providers.

=============================================================================
PROVIDER PATTERN FOR .NET DEVELOPERS
=============================================================================

This is Python's equivalent of an interface. Any class that implements
these methods can be used as a memory store.

Think of it like:
  - C# interface: IMemoryStore
  - Dependency injection: Swap implementations without changing consumers

The Protocol class (from typing) defines the contract. Any class with
matching method signatures is considered compatible - no explicit
inheritance required (structural typing / duck typing).

USAGE:
    # In main.py - wire up the provider you want
    memory_store = InMemoryStore()  # or RedisStore() or CosmosStore()
    orchestrator = OrchestratorAgent(..., memory_store=memory_store)

ADDING NEW PROVIDERS:
    1. Create new file in providers/ (e.g., redis.py)
    2. Implement all methods from IMemoryStore interface
    3. Swap in main.py - no other changes needed
=============================================================================
"""
from typing import Protocol
from .models import ConversationTurn


class IMemoryStore(Protocol):
    """
    Interface for conversation memory storage.
    
    Implementations must provide all these methods.
    The session_id groups turns by conversation/user.
    """
    
    def save_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """
        Save a conversation turn to memory.
        
        Args:
            session_id: Unique identifier for the conversation
            turn: The turn to save
        """
        ...
    
    def get_turns(self, session_id: str, limit: int = 10) -> list[ConversationTurn]:
        """
        Get recent conversation turns.
        
        Args:
            session_id: Unique identifier for the conversation
            limit: Maximum number of turns to return (most recent first)
            
        Returns:
            List of ConversationTurn objects, newest first
        """
        ...
    
    def get_entities(self, session_id: str) -> dict[str, str]:
        """
        Get accumulated entities across all turns.
        
        Args:
            session_id: Unique identifier for the conversation
            
        Returns:
            Dict of entity_type -> value (e.g., {"destination": "Denver"})
        """
        ...
    
    def clear(self, session_id: str) -> None:
        """
        Clear all memory for a session.
        
        Args:
            session_id: Unique identifier for the conversation
        """
        ...
