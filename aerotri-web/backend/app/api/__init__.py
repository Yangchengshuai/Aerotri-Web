from fastapi import APIRouter
from .blocks import router as blocks_router
from .images import router as images_router
from .gpu import router as gpu_router
from .tasks import router as tasks_router
from .results import router as results_router

api_router = APIRouter()

api_router.include_router(blocks_router, prefix="/blocks", tags=["blocks"])
api_router.include_router(images_router, prefix="/blocks", tags=["images"])
api_router.include_router(gpu_router, prefix="/gpu", tags=["gpu"])
api_router.include_router(tasks_router, prefix="/blocks", tags=["tasks"])
api_router.include_router(results_router, prefix="/blocks", tags=["results"])
