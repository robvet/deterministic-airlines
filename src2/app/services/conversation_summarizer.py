"""
Conversation Summarizer - Folds old turns into a progressive summary.

=============================================================================
SLIDING WINDOW + PROGRESSIVE SUMMARIZATION PATTERN
=============================================================================

This service implements the "rolling summary" pattern for long conversations:

PROBLEM:
- Can't send unlimited context to classifier (token limits, cost, distraction)
- But we need to remember important facts from earlier in conversation

SOLUTION:
When the conversation exceeds K turns:
1. Take the oldest turn outside the window
2. Summarize it into a compressed "conversation summary"
3. Remove that turn from the sliding window
4. Classifier sees: summary + last K turns + entities

EXAMPLE:
  Turn 9 arrives:
    - Turn 6 gets folded into summary
    - Window slides to [7, 8, 9]
    - Classifier sees summary(1-6) + turns(7,8,9) + entities

MODEL CHOICE:
Uses the same fast SLM as classification (gpt-4.1-mini):
- Cheap: summarization is frequent but low-stakes
- Fast: doesn't block the main request
- Sufficient: compression doesn't need heavy reasoning

=============================================================================
"""
from ..memory.models import ConversationTurn
from .llm_service import LLMService
from .prompt_template_service import PromptTemplateService


class ConversationSummarizer:
    """
    Folds conversation turns into a progressive summary.
    
    This class handles the "compression" step of the sliding window pattern.
    When a turn falls outside the context window, it gets folded into the
    summary rather than being lost entirely.
    
    WORKSHOP NOTE:
    This demonstrates how to maintain long-term context without sending
    the entire conversation history to the LLM every time.
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        template_service: PromptTemplateService
    ):
        self._llm = llm_service
        self._templates = template_service
        print(f"[ConversationSummarizer] Initialized")
    
    def fold_turn(
        self,
        turn: ConversationTurn,
        existing_summary: str
    ) -> str:
        """
        Fold a single turn into the existing summary.
        
        This is called when a turn "falls off" the sliding window.
        The turn's key facts are compressed into the running summary.
        
        Args:
            turn: The ConversationTurn to fold into summary
            existing_summary: Current summary text (may be empty)
            
        Returns:
            Updated summary string with the turn's facts incorporated
            
        EXAMPLE:
            existing: "- Customer asked about Denver flights"
            turn: user asked to cancel booking IR-D204
            result: "- Customer asked about Denver flights
                     - Customer cancelled booking IR-D204"
        """
        print(f"[ConversationSummarizer] Folding turn into summary: '{turn.user_input[:50]}...'")
        
        # Format entities as readable string
        entities_str = ", ".join(f"{k}={v}" for k, v in turn.entities.items()) if turn.entities else "none"
        
        # Build the summarization prompt
        system_prompt = self._templates.load(
            "summarize_conversation_prompt",
            {
                "existing_summary": existing_summary or "(no prior summary)",
                "user_input": turn.user_input,
                "agent_response": turn.agent_response,
                "intent": turn.intent,
                "entities": entities_str
            }
        )
        
        # Call the SLM for summarization (same fast model as classifier)
        updated_summary = self._llm.complete(
            system_prompt=system_prompt,
            user_message="Generate the updated summary.",
            use_classifier_model=True  # gpt-4.1-mini - fast and cheap
        )
        
        print(f"[ConversationSummarizer] ✓ Summary updated ({len(updated_summary)} chars)")
        return updated_summary.strip()
