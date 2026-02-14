"""
In-Memory Store - Simple dict-based memory for development/testing.

=============================================================================
IN-MEMORY PROVIDER
=============================================================================

This is the simplest possible implementation of MemoryStore.
Uses Python dicts - fast, no dependencies, but:
  - Lost when process restarts
  - Not shared across instances
  - No persistence

Perfect for:
  - Local development
  - Testing
  - Workshop demos
  - Single-instance deployments

For production, swap to RedisStore or CosmosStore.
=============================================================================
"""
from ..models import ConversationTurn


class InMemoryStore:
    """
    In-memory implementation of MemoryStore protocol.
    
    Stores conversation turns in a simple dict.
    Data is lost when the process ends.
    """
    
    def __init__(self):
        # session_id -> list of turns
        self._sessions: dict[str, list[ConversationTurn]] = {}
        # session_id -> progressive summary
        self._summaries: dict[str, str] = {}
        print(f"[InMemoryStore] Initialized")
    
    def save_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Save a turn to the session's history."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        self._sessions[session_id].append(turn)
        print(f"[InMemoryStore] Saved turn for session {session_id} (total: {len(self._sessions[session_id])})")
    
    def get_turns(self, session_id: str, limit: int = 10) -> list[ConversationTurn]:
        """Get recent turns, newest first."""
        if session_id not in self._sessions:
            return []
        
        # Return most recent 'limit' turns, reversed so newest is first
        turns = self._sessions[session_id][-limit:]
        return list(reversed(turns))
    
    def get_entities(self, session_id: str) -> dict[str, str]:
        """
        Accumulate entities across all turns in the session.
        
        Later values override earlier ones (e.g., if user changes destination).
        """
        if session_id not in self._sessions:
            return {}
        
        accumulated: dict[str, str] = {}
        for turn in self._sessions[session_id]:
            accumulated.update(turn.entities)
        
        return accumulated
    
    def clear(self, session_id: str) -> None:
        """Clear all turns for this session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._summaries:
            del self._summaries[session_id]
        print(f"[InMemoryStore] Cleared session {session_id}")
    
    def get_summary(self, session_id: str) -> str:
        """Get the progressive summary for this session."""
        return self._summaries.get(session_id, "")
    
    def save_summary(self, session_id: str, summary: str) -> None:
        """Save the updated progressive summary."""
        self._summaries[session_id] = summary
        print(f"[InMemoryStore] Saved summary for session {session_id} ({len(summary)} chars)")
    
    def pop_oldest_turn(self, session_id: str) -> "ConversationTurn | None":
        """Remove and return the oldest turn."""
        if session_id not in self._sessions or not self._sessions[session_id]:
            return None
        
        oldest = self._sessions[session_id].pop(0)  # Remove from front (oldest)
        print(f"[InMemoryStore] Popped oldest turn from session {session_id}")
        return oldest
    
    def get_turn_count(self, session_id: str) -> int:
        """Get total number of turns stored."""
        if session_id not in self._sessions:
            return 0
        return len(self._sessions[session_id])
