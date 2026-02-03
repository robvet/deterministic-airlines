"""
Application Runner with Crash-Safe Port Cleanup

This script wraps uvicorn to ensure port cleanup happens even on crashes.
Use this instead of calling uvicorn directly.

Features:
- Port cleanup on startup (kills orphan processes)
- Port cleanup on shutdown (graceful or crash)
- Signal handlers for Ctrl+C and termination
- OpenTelemetry integration with Azure Application Insights
- LifespanManager for browser auto-open

Usage:
    python run.py
    
    Or from start-backend.ps1:
    python run.py
"""
import sys
import atexit
import signal

from dotenv import load_dotenv
load_dotenv()  # Load .env before any other imports

from app.config.settings import settings
from app.utils.port_cleanup import PortCleanup


PORT = settings.server_port


def cleanup_on_exit():
    """Cleanup handler registered with atexit."""
    print(f"\n[CLEANUP] Releasing port {PORT}...")
    PortCleanup.kill_process_on_port(PORT)


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM gracefully."""
    print(f"\n[SIGNAL] Received signal {signum}, cleaning up...")
    cleanup_on_exit()
    sys.exit(0)


def create_app():
    """
    Create and configure the FastAPI application.
    
    This is separated from main() so the app can be imported
    directly for testing or alternative runners.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    from app.observability.telemetry_service import setup_telemetry
    from app.utils.lifespan_manager import LifespanManager
    from app.api import router
    
    # Initialize telemetry (Facade Pattern - see telemetry_service.py)
    setup_telemetry()
    
    # Lifespan manager handles startup/shutdown (port cleanup, browser, telemetry flush)
    # OPEN_BROWSER env var controls this - defaults to False (production-safe)
    lifespan_manager = LifespanManager(
        port=PORT,
        open_browser=settings.open_browser,  # Auto-open Swagger UI (set OPEN_BROWSER=true for dev)
        flush_telemetry=True,
        frontend_url=None,  # Streamlit runs separately
    )
    
    app = FastAPI(
        title="Deterministic Airlines Agent API",
        description="Deterministic AI agent for airline customer service",
        version="1.0.0",
        lifespan=lifespan_manager.lifespan,
    )
    
    # Instrument FastAPI for OpenTelemetry tracing (traces all HTTP requests)
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        print("[TELEMETRY] FastAPI instrumentation enabled")
    except ImportError:
        print("[TELEMETRY] FastAPI instrumentation not available")
    
    # CORS for Streamlit UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routes
    app.include_router(router)
    
    return app


# Create app at module level for uvicorn import
app = create_app()


def main():
    """Run the application with crash-safe port cleanup."""
    import uvicorn
    
    # Register cleanup for normal exit
    atexit.register(cleanup_on_exit)
    
    # Register signal handlers for Ctrl+C and termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clean port before starting (in case of previous crash)
    print(f"[STARTUP] Cleaning port {PORT}...")
    PortCleanup.kill_process_on_port(PORT)
    
    print(f"[STARTUP] Starting Deterministic Airlines API on http://localhost:{PORT}")
    print(f"[STARTUP] Swagger UI: http://localhost:{PORT}/docs")
    
    try:
        uvicorn.run(
            app,  # Use the already-created app instance
            host=settings.server_host,
            port=PORT,
            reload=False,  # Disable reload when running app instance directly
        )
    except Exception as e:
        print(f"[CRASH] Application crashed: {e}")
        raise
    finally:
        # This runs even if uvicorn crashes
        cleanup_on_exit()


if __name__ == "__main__":
    main()
