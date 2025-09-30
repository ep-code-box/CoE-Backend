from contextlib import asynccontextmanager
from fastapi import FastAPI

# Import services
from services.flow_router_service import FlowRouterService
from services.scheduler_service import SchedulerService
from services.pii_service import initialize_pid, terminate_pid

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifespan events (startup and shutdown).
    This is the recommended way to handle startup/shutdown logic in modern FastAPI.
    """
    # --- Startup Logic ---
    print("--- Running startup events via lifespan manager ---")
    
    # 1. Initialize services
    flow_router_service = FlowRouterService(app)
    scheduler_service = SchedulerService(flow_router_service)
    
    # 2. Store service in app state for dependency injection
    app.state.flow_router_service = flow_router_service
    
    # 3. Perform initial sync and start the background scheduler
    scheduler_service.sync_routes_from_db()
    scheduler_service.start()

    # 4. Initialize PID resources once per process
    initialize_pid()
    
    print("--- Startup complete ---")
    
    yield # The application runs here
    
    # --- Shutdown Logic ---
    print("--- Running shutdown events via lifespan manager ---")
    scheduler_service.stop()
    terminate_pid()
    print("--- Shutdown complete ---")
