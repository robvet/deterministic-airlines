"""
LifespanManager - Reusable FastAPI lifespan handler.

Handles common startup/shutdown tasks:
- Port cleanup (kill orphan processes)
- Browser auto-open for Swagger UI and optional frontend
- Telemetry flush on shutdown (if OpenTelemetry is installed)

Usage:
    lifespan_manager = LifespanManager(port=8000, open_browser=True, frontend_url="http://localhost:3000")
    app = FastAPI(lifespan=lifespan_manager.lifespan)
"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from .port_cleanup import PortCleanup
from .browser_opener import BrowserOpener

# OpenTelemetry is optional - only import if available
try:
    from opentelemetry import trace
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False


class LifespanManager:
    """
    Manages FastAPI application lifespan events.
    
    Configurable startup/shutdown behavior for any FastAPI app.
    """

    def __init__(
        self,
        port: int,
        open_browser: bool = True,
        flush_telemetry: bool = True,
        frontend_url: Optional[str] = None,
    ) -> None:
        """
        Initialize the lifespan manager.
        
        Args:
            port: The port the app runs on (for cleanup)
            open_browser: Whether to auto-open Swagger UI on startup
            flush_telemetry: Whether to flush OpenTelemetry on shutdown
            frontend_url: Optional frontend URL to open (e.g., "http://localhost:3000")
        """
        self._port = port
        self._open_browser = open_browser
        self._flush_telemetry = flush_telemetry
        self._frontend_url = frontend_url

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """
        Async context manager for FastAPI lifespan.
        
        Startup: Cleans port, optionally opens browser
        Shutdown: Flushes telemetry, cleans port
        """
        # --- STARTUP runs when app starts ---
        PortCleanup.kill_process_on_port(self._port)
        if self._open_browser:
            BrowserOpener.open_swagger_ui_background(port=self._port, delay_seconds=2.0)
        if self._frontend_url:
            # Stagger frontend opening to avoid browser conflicts
            await BrowserOpener.open_after_delay(self._frontend_url, delay_seconds=3.5)
        
        yield  # Yield statement is about control flow
               # Upon yield, control is returned to FastAPI and the app code runs
              
               # --- SHUTDOWN runs when when app stops ---
        if self._flush_telemetry:
            self._shutdown_telemetry()
        PortCleanup.kill_process_on_port(self._port)

    def _shutdown_telemetry(self) -> None:
        """Flush pending telemetry data before shutdown."""
        if not HAS_OPENTELEMETRY:
            return
        tracer_provider = trace.get_tracer_provider()
        # Similar to Flush() in C# or Java telemetry clients
        if hasattr(tracer_provider, 'shutdown'):
            tracer_provider.shutdown()
