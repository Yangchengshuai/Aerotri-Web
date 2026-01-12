"""System monitoring API endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Block, BlockStatus, get_db
from ..schemas import GPUInfo
from ..services.system_monitor import system_monitor

router = APIRouter()


class GPUStatusResponse(BaseModel):
    """GPU status in system response."""
    index: int
    name: str
    memory_total: int  # MB
    memory_used: int  # MB
    memory_free: int  # MB
    utilization: int  # percentage
    is_available: bool


class SystemStatusResponse(BaseModel):
    """Complete system status response."""
    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float
    gpus: List[GPUStatusResponse]
    gpu_count: int
    running_tasks: int
    queued_tasks: int
    timestamp: datetime


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """Get current system status including CPU, memory, disk, GPU, and task counts.
    
    Returns:
        SystemStatusResponse with all system metrics
    """
    # Get system metrics
    status = system_monitor.get_system_status()
    
    # Get task counts from database
    running_result = await db.execute(
        select(func.count(Block.id))
        .where(Block.status == BlockStatus.RUNNING)
    )
    running_count = running_result.scalar() or 0
    
    queued_result = await db.execute(
        select(func.count(Block.id))
        .where(Block.status == BlockStatus.QUEUED)
    )
    queued_count = queued_result.scalar() or 0
    
    # Convert GPU dicts to response models
    gpus = []
    for gpu_data in status.get("gpus", []):
        gpus.append(GPUStatusResponse(
            index=gpu_data.get("index", 0),
            name=gpu_data.get("name", "Unknown"),
            memory_total=gpu_data.get("memory_total", 0),
            memory_used=gpu_data.get("memory_used", 0),
            memory_free=gpu_data.get("memory_free", 0),
            utilization=gpu_data.get("utilization", 0),
            is_available=gpu_data.get("is_available", False),
        ))
    
    return SystemStatusResponse(
        cpu_percent=status["cpu_percent"],
        memory_total_gb=status["memory_total_gb"],
        memory_used_gb=status["memory_used_gb"],
        memory_available_gb=status["memory_available_gb"],
        memory_percent=status["memory_percent"],
        disk_total_gb=status["disk_total_gb"],
        disk_used_gb=status["disk_used_gb"],
        disk_free_gb=status["disk_free_gb"],
        disk_percent=status["disk_percent"],
        gpus=gpus,
        gpu_count=status["gpu_count"],
        running_tasks=running_count,
        queued_tasks=queued_count,
        timestamp=datetime.utcnow(),
    )
