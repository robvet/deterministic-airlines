"""
Booking Data - Mock flight inventory and itineraries for demos.

Contains:
- MOCK_ITINERARIES: Customer booking scenarios (disrupted flight, on-time flight)
- AVAILABLE_FLIGHTS: Flights that can be booked
- Helper functions for data access
"""
from copy import deepcopy


# =============================================================================
# MOCK ITINERARIES - Existing customer bookings
# =============================================================================
MOCK_ITINERARIES = {
    "disrupted": {
        "name": "Paris to New York to Austin",
        "passenger_name": "Morgan Lee",
        "confirmation_number": "IR-D204",
        "seat_number": "14C",
        "baggage_tag": "BG20488",
        "segments": [
            {
                "flight_number": "PA441",
                "origin": "Paris (CDG)",
                "destination": "New York (JFK)",
                "departure": "2024-12-09 14:10",
                "arrival": "2024-12-09 17:40",
                "status": "Delayed 5 hours due to weather, expected departure 19:55",
                "gate": "B18",
            },
            {
                "flight_number": "NY802",
                "origin": "New York (JFK)",
                "destination": "Austin (AUS)",
                "departure": "2024-12-09 19:10",
                "arrival": "2024-12-09 22:35",
                "status": "Connection missed because of first leg delay",
                "gate": "C7",
            },
        ],
        "rebook_options": [
            {
                "flight_number": "NY950",
                "origin": "New York (JFK)",
                "destination": "Austin (AUS)",
                "departure": "2024-12-10 09:45",
                "arrival": "2024-12-10 12:30",
                "seat": "2A (front row)",
                "note": "Partner flight secured with auto-reaccommodation for disrupted travelers",
            },
            {
                "flight_number": "NY982",
                "origin": "New York (JFK)",
                "destination": "Austin (AUS)",
                "departure": "2024-12-10 13:20",
                "arrival": "2024-12-10 16:05",
                "seat": "3C",
                "note": "Backup option if the morning flight is full",
            },
        ],
        "vouchers": {
            "hotel": "Overnight hotel covered up to $180 near JFK Terminal 5 partner hotel",
            "meal": "$60 meal credit for the delay",
            "ground": "$40 ground transport credit to the hotel",
        },
    },
    "on_time": {
        "name": "On-time commuter flight",
        "passenger_name": "Taylor Lee",
        "confirmation_number": "LL0EZ6",
        "seat_number": "23A",
        "baggage_tag": "BG55678",
        "segments": [
            {
                "flight_number": "FLT-123",
                "origin": "San Francisco (SFO)",
                "destination": "Los Angeles (LAX)",
                "departure": "2024-12-09 16:10",
                "arrival": "2024-12-09 17:35",
                "status": "On time and operating as scheduled",
                "gate": "A10",
            }
        ],
        "rebook_options": [],
        "vouchers": {},
    },
}


# =============================================================================
# AVAILABLE FLIGHTS - Inventory for new bookings
# =============================================================================
AVAILABLE_FLIGHTS = [
    {
        "flight_number": "DA100",
        "origin": "New York (JFK)",
        "destination": "Los Angeles (LAX)",
        "departure": "2024-12-15 08:00",
        "arrival": "2024-12-15 11:30",
        "price": 299.00,
        "seats_available": 45,
        "class": "Economy",
    },
    {
        "flight_number": "DA101",
        "origin": "New York (JFK)",
        "destination": "Los Angeles (LAX)",
        "departure": "2024-12-15 14:00",
        "arrival": "2024-12-15 17:30",
        "price": 349.00,
        "seats_available": 22,
        "class": "Economy",
    },
    {
        "flight_number": "DA200",
        "origin": "Los Angeles (LAX)",
        "destination": "Chicago (ORD)",
        "departure": "2024-12-16 09:00",
        "arrival": "2024-12-16 14:45",
        "price": 275.00,
        "seats_available": 60,
        "class": "Economy",
    },
    {
        "flight_number": "DA305",
        "origin": "Chicago (ORD)",
        "destination": "Miami (MIA)",
        "departure": "2024-12-17 11:00",
        "arrival": "2024-12-17 15:30",
        "price": 225.00,
        "seats_available": 35,
        "class": "Economy",
    },
]


def get_itinerary_by_confirmation(confirmation_number: str) -> dict | None:
    """
    Look up an itinerary by confirmation number.
    
    Args:
        confirmation_number: The booking confirmation code
        
    Returns:
        Itinerary dict if found, None otherwise
    """
    for key, itinerary in MOCK_ITINERARIES.items():
        if itinerary.get("confirmation_number", "").upper() == confirmation_number.upper():
            return deepcopy(itinerary)
    return None


def get_itinerary_by_flight(flight_number: str) -> tuple[str, dict] | None:
    """
    Find an itinerary containing a specific flight number.
    
    Args:
        flight_number: The flight number to search for
        
    Returns:
        Tuple of (scenario_key, itinerary) if found, None otherwise
    """
    if not flight_number:
        return None
    for key, itinerary in MOCK_ITINERARIES.items():
        for segment in itinerary.get("segments", []):
            if segment.get("flight_number", "").upper() == flight_number.upper():
                return key, deepcopy(itinerary)
    return None


def get_available_flights(origin: str = None, destination: str = None) -> list[dict]:
    """
    Get available flights, optionally filtered by origin/destination.
    
    Args:
        origin: Filter by origin city/airport (partial match)
        destination: Filter by destination city/airport (partial match)
        
    Returns:
        List of matching available flights
    """
    flights = deepcopy(AVAILABLE_FLIGHTS)
    
    if origin:
        flights = [f for f in flights if origin.upper() in f["origin"].upper()]
    if destination:
        flights = [f for f in flights if destination.upper() in f["destination"].upper()]
    
    return flights


def get_formatted_available_flights() -> str:
    """
    Get available flights formatted for LLM context.
    
    Returns:
        Multi-line string of available flights
    """
    lines = ["Available Flights:"]
    for flight in AVAILABLE_FLIGHTS:
        lines.append(
            f"- {flight['flight_number']}: {flight['origin']} → {flight['destination']} "
            f"on {flight['departure']} (${flight['price']}, {flight['seats_available']} seats)"
        )
    return "\n".join(lines)
