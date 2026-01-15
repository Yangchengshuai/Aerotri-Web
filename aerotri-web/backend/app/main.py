"""Main FastAPI application."""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .ws import progress_router, visualization_router
from .models.database import init_db
from .conf.validation import validate_on_startup
from .services.task_runner import task_runner
from .services.openmvs_runner import openmvs_runner
from .services.gs_runner import gs_runner
from .services.tiles_runner import tiles_runner
from .services.queue_scheduler import queue_scheduler
from .services.notification import notification_manager, periodic_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup

    # 验证配置并创建必要目录
    try:
        warnings = validate_on_startup()
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
    except RuntimeError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # Initialize database
    await init_db()
    
    # Initialize notification service (safe to call, no-ops if disabled)
    notification_manager.initialize()
    
    # Recover orphaned tasks from previous session
    await task_runner.recover_orphaned_tasks()
    # Recover orphaned reconstruction tasks
    await openmvs_runner.recover_orphaned_reconstructions()
    # Recover orphaned 3DGS training tasks
    await gs_runner.recover_orphaned_gs_tasks()
    # Recover orphaned 3D Tiles conversion tasks
    await tiles_runner.recover_orphaned_tiles_tasks()
    
    # Start queue scheduler for automatic task dispatching
    await queue_scheduler.start()
    
    # Send startup notification (safe to call, no-ops if disabled)
    try:
        await notification_manager.notify_backend_startup(version="1.0.0")
    except Exception as e:
        logger.warning(f"Failed to send startup notification: {e}")
    
    # Start periodic notification scheduler (if notification is enabled)
    if notification_manager.enabled:
        from .config import config_loader
        periodic_config = config_loader.get("notification", "notification.periodic", default={})
        periodic_scheduler.configure(periodic_config)
        await periodic_scheduler.start()
    
    yield
    
    # Shutdown
    # Stop periodic scheduler first
    try:
        await periodic_scheduler.stop()
    except Exception as e:
        logger.warning(f"Failed to stop periodic scheduler: {e}")
    
    # Send shutdown notification before stopping services
    try:
        await notification_manager.notify_backend_shutdown()
    except Exception as e:
        logger.warning(f"Failed to send shutdown notification: {e}")
    
    await queue_scheduler.stop()


app = FastAPI(
    title="AeroTri Web",
    description="Web-based Aerotriangulation Tool using COLMAP/GLOMAP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - MUST be before app.include_router()
# This ensures all responses, including FileResponse, have CORS headers
frontend_origins = [
    # Local development
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Optional demo / production origins (can be overridden via env)
demo_frontend_origin = os.getenv("AEROTRI_FRONTEND_ORIGIN")
if demo_frontend_origin:
    frontend_origins.append(demo_frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,  # Allow credentials when using specific origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers to the client
)

# GZip middleware (important for large JSON payloads like point clouds)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# API routes
app.include_router(api_router, prefix="/api")

# WebSocket routes
app.include_router(progress_router)
app.include_router(visualization_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AeroTri Web API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
