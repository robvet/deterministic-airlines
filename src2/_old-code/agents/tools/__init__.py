"""
Tools package - Domain-organized agent tools.

Tools are shared resources that can be used by multiple agents.
Each module groups related functionality by business domain.

Usage:
    from .tools import faq_lookup_tool, flight_status_tool
    # or import all:
    from .tools import *
"""

# FAQ domain
from .faq_tools import faq_lookup_tool

# Flight domain
from .flight_tools import flight_status_tool, get_matching_flights, get_trip_details

# Booking domain
from .booking_tools import book_new_flight, cancel_flight

# Seat domain
from .seat_tools import update_seat, assign_special_service_seat, display_seat_map

# Compensation domain
from .compensation_tools import issue_compensation

# Baggage domain (no agent yet - workshop exercise)
from .baggage_tools import baggage_tool

__all__ = [
    # FAQ
    "faq_lookup_tool",
    # Flight
    "flight_status_tool",
    "get_matching_flights",
    "get_trip_details",
    # Booking
    "book_new_flight",
    "cancel_flight",
    # Seat
    "update_seat",
    "assign_special_service_seat",
    "display_seat_map",
    # Compensation
    "issue_compensation",
    # Baggage
    "baggage_tool",
]
