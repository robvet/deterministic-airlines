"""
Few-Shot Prompt Converter

Wraps a plain prompt with relevant examples to guide the LLM's response format and tone.
Few-shot prompting is one of the most effective techniques for steering model behavior.

WORKSHOP NOTES:
- Zero-shot: Just ask the question (no examples)
- Few-shot: Provide 2-3 examples first, then ask
- Few-shot typically improves consistency and format adherence

Usage:
    converter = FewShotConverter()
    enhanced = converter.convert(
        prompt="What's the baggage policy?",
        category="faq"  # Picks relevant examples
    )
"""

# Pre-defined examples for different categories
EXAMPLES = {
    "faq": [
        {
            "customer": "What's your baggage policy?",
            "agent": "For domestic flights, you're allowed 1 carry-on bag (22x14x9 inches) and 1 personal item at no charge. Checked bags are $35 for the first bag and $45 for additional bags."
        },
        {
            "customer": "Is there WiFi on flights?",
            "agent": "Yes, WiFi is available on most of our aircraft. Basic messaging is free, and full internet access is $8.99 for the entire flight."
        },
    ],
    "booking": [
        {
            "customer": "I want to book a flight to Chicago",
            "agent": "I'd be happy to help you book a flight to Chicago. I found flight DA200 departing from LAX to ORD at $275. Would you like me to proceed with this booking?"
        },
        {
            "customer": "Book me on flight DA100",
            "agent": "I've booked you on flight DA100 from JFK to LAX. Your confirmation number is DA100-7829. The total was $299. Is there anything else you need?"
        },
    ],
    "cancellation": [
        {
            "customer": "Cancel my booking ABC123",
            "agent": "I've cancelled your booking ABC123. Since you're within the 24-hour cancellation window, you'll receive a full refund to your original payment method within 5-7 business days."
        },
        {
            "customer": "I need to cancel my trip",
            "agent": "I can help you cancel. Could you please provide your booking reference number? It's a 6-character code from your confirmation email."
        },
    ],
    "compensation": [
        {
            "customer": "My flight was delayed 4 hours",
            "agent": "I'm sorry for the delay. For delays over 3 hours, you're entitled to a $100 travel voucher. I've applied this to your account. For delays over 5 hours, you may also request meal reimbursement up to $30."
        },
        {
            "customer": "I missed my connection because of your delay",
            "agent": "I sincerely apologize for the missed connection. I've rebooked you on the next available flight at no additional cost and added a $150 voucher for the inconvenience. Would you like me to arrange hotel accommodation if needed?"
        },
    ],
    "general": [
        {
            "customer": "What time does my flight leave?",
            "agent": "Your flight DA100 is scheduled to depart at 2:30 PM from Gate B12. Boarding begins 30 minutes before departure. Please arrive at the gate by 2:00 PM."
        },
        {
            "customer": "Can I change my seat?",
            "agent": "I'd be happy to help you change your seat. You're currently in 14C (aisle). I see 7A and 7F (window seats) are available. Which would you prefer?"
        },
    ],
}


class FewShotConverter:
    """
    Converts plain prompts into few-shot prompts with relevant examples.
    """
    
    def __init__(self):
        self._examples = EXAMPLES
    
    def get_categories(self) -> list[str]:
        """Return available example categories."""
        return list(self._examples.keys())
    
    def convert(self, prompt: str, category: str = "general", num_examples: int = 2) -> str:
        """
        Wrap a prompt with few-shot examples.
        
        Args:
            prompt: The user's question
            category: Which example set to use (faq, booking, cancellation, compensation, general)
            num_examples: How many examples to include (1-3)
            
        Returns:
            Enhanced prompt with examples
        """
        examples = self._examples.get(category, self._examples["general"])
        examples = examples[:num_examples]
        
        # Build the few-shot prompt
        lines = ["Here are examples of how to respond to customer inquiries:\n"]
        
        for i, ex in enumerate(examples, 1):
            lines.append(f"Example {i}:")
            lines.append(f"Customer: \"{ex['customer']}\"")
            lines.append(f"Agent: \"{ex['agent']}\"")
            lines.append("")
        
        lines.append("Now respond to this customer inquiry following the same style and format:")
        lines.append(f"Customer: \"{prompt}\"")
        lines.append("Agent:")
        
        return "\n".join(lines)
    
    def convert_with_custom_examples(
        self, 
        prompt: str, 
        examples: list[dict]
    ) -> str:
        """
        Wrap a prompt with custom examples.
        
        Args:
            prompt: The user's question
            examples: List of {"customer": "...", "agent": "..."} dicts
            
        Returns:
            Enhanced prompt with examples
        """
        lines = ["Here are examples of how to respond:\n"]
        
        for i, ex in enumerate(examples, 1):
            lines.append(f"Example {i}:")
            lines.append(f"Customer: \"{ex.get('customer', '')}\"")
            lines.append(f"Agent: \"{ex.get('agent', '')}\"")
            lines.append("")
        
        lines.append("Now respond following the same style:")
        lines.append(f"Customer: \"{prompt}\"")
        lines.append("Agent:")
        
        return "\n".join(lines)
