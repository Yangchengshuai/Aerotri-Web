"""GPU monitoring API endpoints."""
from fastapi import APIRouter, HTTPException
from ..schemas import GPUInfo, GPUListResponse
from ..services.gpu_service import GPUService

router = APIRouter()


@router.get("/status", response_model=GPUListResponse)
async def get_gpu_status():
    """Get status of all available GPUs."""
    try:
        gpus = GPUService.get_all_gpus()
        return GPUListResponse(gpus=gpus)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get GPU status: {str(e)}"
        )


@router.get("/status/{gpu_index}", response_model=GPUInfo)
async def get_single_gpu_status(gpu_index: int):
    """Get status of a specific GPU."""
    try:
        gpu = GPUService.get_gpu(gpu_index)
        if not gpu:
            raise HTTPException(
                status_code=404,
                detail=f"GPU {gpu_index} not found"
            )
        return gpu
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get GPU status: {str(e)}"
        )
