"""
Observability package - Telemetry, tracing, and metrics.

Exports:
- setup_telemetry: Call once at startup to initialize Azure Application Insights
- telemetry_service: Singleton for accessing tracer and meter
"""
from .telemetry_service import setup_telemetry, telemetry_service

__all__ = ["setup_telemetry", "telemetry_service"]
