"""
FAQ Grounding Data

This is the knowledge base that the LLM uses to answer FAQ questions.
The LLM can ONLY use information from this data - it cannot make things up.

In a real application, this might come from:
- A database
- A vector store / RAG system  
- An API call to a knowledge management system

For the workshop, we use a simple dictionary to keep things clear.
"""

FAQ_DATA = {
    "baggage": (
        "Baggage Policy: "
        "You are allowed one carry-on bag and one personal item. "
        "Carry-on must be under 22 x 14 x 9 inches. "
        "Checked bags: first bag free, second bag $35. "
        "Overweight bags (over 50 lbs) incur a $75 fee. "
        "If a bag is delayed or missing, file a claim at the airport "
        "or with customer service, and we will track it for delivery."
    ),
    
    "wifi": (
        "WiFi Policy: "
        "We offer complimentary WiFi on all flights. "
        "Connect to the 'PacificAir-WiFi' network. "
        "Streaming quality is available on flights over 2 hours. "
        "For connectivity issues, try disconnecting and reconnecting, "
        "or ask a flight attendant for assistance."
    ),
    
    "seats": (
        "Seating Information: "
        "Our aircraft have 120 seats total. "
        "Business class: 22 seats in rows 1-4. "
        "Economy Plus: 24 seats in rows 5-8, with extra legroom. "
        "Economy: 74 seats in rows 9-25. "
        "Exit rows are rows 4 and 16 - passengers must be able to assist in emergencies. "
        "Seat selection is free for Business, $15 for preferred Economy seats."
    ),
    
    "compensation": (
        "Delay and Compensation Policy: "
        "For delays over 2 hours, we provide meal vouchers. "
        "For delays over 4 hours or overnight, we provide hotel accommodation "
        "and ground transportation. "
        "If a delay causes a missed connection, we will rebook you on the next "
        "available flight at no charge and open a compensation case. "
        "Compensation may include travel credits or frequent flyer miles, "
        "depending on the circumstances."
    ),
    
    "refunds": (
        "Refund Policy: "
        "Full refund available within 24 hours of booking. "
        "Refundable tickets can be cancelled anytime for full refund. "
        "Non-refundable tickets receive travel credit minus a $75 change fee. "
        "Refunds are processed within 7-10 business days. "
        "For flight cancellations by the airline, full refund is automatic."
    ),
    
    "pets": (
        "Pet Policy: "
        "Small dogs and cats are allowed in cabin in an approved carrier. "
        "Carrier must fit under the seat (18 x 11 x 11 inches max). "
        "Pet fee is $95 each way. "
        "Limit of 2 pets per cabin - book early. "
        "Service animals fly free with proper documentation. "
        "No pets in Business class except service animals."
    )
}


def get_formatted_faq_data() -> str:
    """
    Format the FAQ data as a readable string for prompt injection.
    
    Returns a string like:
        [BAGGAGE]: Baggage Policy: You are allowed...
        [WIFI]: WiFi Policy: We offer...
    """
    lines = []
    for topic, content in FAQ_DATA.items():
        lines.append(f"[{topic.upper()}]: {content}")
    return "\n\n".join(lines)
