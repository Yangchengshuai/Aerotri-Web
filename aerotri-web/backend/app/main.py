"""Main FastAPI application."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .ws import progress_router
from .models.database import init_db
from .services.task_runner import task_runner
from .services.openmvs_runner import openmvs_runner
from .services.gs_runner import gs_runner


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    
    # Ensure data directories exist
    os.makedirs("/root/work/aerotri-web/data/outputs", exist_ok=True)
    os.makedirs("/root/work/aerotri-web/data/thumbnails", exist_ok=True)
    
    # Recover orphaned tasks from previous session
    await task_runner.recover_orphaned_tasks()
    # Recover orphaned reconstruction tasks
    await openmvs_runner.recover_orphaned_reconstructions()
    # Recover orphaned 3DGS training tasks
    await gs_runner.recover_orphaned_gs_tasks()
    
    yield
    
    # Shutdown
    pass


app = FastAPI(
    title="AeroTri Web",
    description="Web-based Aerotriangulation Tool using COLMAP/GLOMAP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip middleware (important for large JSON payloads like point clouds)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# API routes
app.include_router(api_router, prefix="/api")

# WebSocket routes
app.include_router(progress_router)


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
