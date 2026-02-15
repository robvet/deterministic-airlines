"""
Context Manager - Owns all conversation context operations.

=============================================================================
SINGLE RESPONSIBILITY
=============================================================================

This class is the ONE place that manages conversation context:
  - Loading context (summary, entities, recent turns) before classification
  - Saving turns after every response
  - Progressive summarization (folding old turns into compressed summary)

The orchestrator calls load_context() and save_turn() — it has
NO KNOWLEDGE of how context is stored, retrieved, or compressed.

FOR C# DEVELOPERS:
Think of this as a UnitOfWork or ContextService that wraps the
underlying IMemoryStore and adds business logic (folding, windowing).

EXTENSIBILITY:
Future context engineering features belong here:
  - Entity decay / relevance scoring
  - Context prioritization
  - Cross-session memory
  - RAG-based long-term recall
=============================================================================
"""
from ..models.classification import ClassificationResponse
from ..services.conversation_summarizer import ConversationSummarizer
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService
from ..config.settings import settings
from .imemory_store import IMemoryStore
from .models import ConversationTurn


class ContextManager:
    """
    Manages all conversation context operations.

    Wraps IMemoryStore with business logic for context loading,
    turn persistence, and progressive summarization.

    ARCHITECTURAL PRINCIPLE:
    Self-contained — could be dropped into another project,
    configured with an IMemoryStore + LLM services, and just work.
    Creates ConversationSummarizer internally.
    """

    def __init__(
        self,
        memory_store: IMemoryStore,
        llm_service: LLMService,
        template_service: PromptTemplateService
    ):
        self._memory = memory_store
        self._summarizer = ConversationSummarizer(llm_service, template_service)
        print("[ContextManager] Initialized")

    def load_context(
        self, session_id: str
    ) -> tuple[str, dict[str, str], list[ConversationTurn]]:
        """
        Load all conversation context for a session.

        Returns everything the classifier needs to make
        an informed routing decision for follow-up questions.

        Args:
            session_id: Unique identifier for the conversation

        Returns:
            Tuple of (conversation_summary, session_entities, recent_turns)
        """
        conversation_summary = self._memory.get_summary(session_id)
        session_entities = self._memory.get_entities(session_id)
        recent_turns = self._memory.get_turns(
            session_id, limit=settings.context_window_size
        )

        if session_entities or recent_turns or conversation_summary:
            has_summary = "with summary" if conversation_summary else "no summary"
            print(
                f"[ContextManager] Loaded context: "
                f"{len(session_entities)} entities, "
                f"{len(recent_turns)} recent turns, {has_summary}"
            )

        return conversation_summary, session_entities, recent_turns

    def save_turn(
        self,
        session_id: str,
        user_input: str,
        agent_answer: str,
        classification: ClassificationResponse,
        tool_reasoning: str | None = None
    ) -> None:
        """
        Save a conversation turn and handle progressive summarization.

        Builds a ConversationTurn from the provided data, saves it
        to memory, then checks if the sliding window overflowed.
        If it did, the oldest turn is folded into the summary.

        Args:
            session_id: Unique identifier for the conversation
            user_input: Raw user input
            agent_answer: Final answer text sent to user
            classification: Classification result (data contract)
            tool_reasoning: Optional reasoning from the executed tool
        """
        # Convert entities list to dict for storage
        entities_dict = {
            e.type: e.value for e in classification.entities
        }

        turn = ConversationTurn(
            user_input=user_input,
            agent_response=agent_answer,
            intent=classification.intent,
            confidence=classification.confidence,
            rewritten_prompt=classification.rewritten_prompt,
            entities=entities_dict,
            classification_reasoning=classification.reasoning,
            tool_reasoning=tool_reasoning
        )

        self._memory.save_turn(session_id, turn)
        self._fold_if_window_overflows(session_id)

    def _fold_if_window_overflows(self, session_id: str) -> None:
        """
        Fold the oldest turn into the summary if window overflows.

        SLIDING WINDOW + PROGRESSIVE SUMMARIZATION PATTERN:
        - We keep exactly K turns in the sliding window
        - When turn K+1 arrives, turn 1 gets folded into summary
        - Summary is compressed text, not full conversation

        Uses ConversationSummarizer with the fast SLM (gpt-4.1-mini).
        """
        turn_count = self._memory.get_turn_count(session_id)
        window_size = settings.context_window_size

        if turn_count <= window_size:
            return

        print(
            f"[ContextManager] Window overflow "
            f"({turn_count} > {window_size}) - folding oldest turn"
        )

        oldest_turn = self._memory.pop_oldest_turn(session_id)
        if not oldest_turn:
            return

        existing_summary = self._memory.get_summary(session_id)
        updated_summary = self._summarizer.fold_turn(
            oldest_turn, existing_summary
        )
        self._memory.save_summary(session_id, updated_summary)

        print(
            f"[ContextManager] ✓ Folded turn into summary, "
            f"window now has {self._memory.get_turn_count(session_id)} turns"
        )
