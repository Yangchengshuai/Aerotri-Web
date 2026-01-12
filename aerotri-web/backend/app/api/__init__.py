from fastapi import APIRouter

from .blocks import router as blocks_router
from .filesystem import router as filesystem_router
from .georef import router as georef_router
from .gpu import router as gpu_router
from .images import router as images_router
from .partitions import router as partitions_router
from .reconstruction import router as reconstruction_router
from .recon_versions import router as recon_versions_router
from .gs import router as gs_router
from .gs_tiles import router as gs_tiles_router
from .tiles import router as tiles_router
from .results import router as results_router
from .tasks import router as tasks_router
from .queue import router as queue_router
from .system import router as system_router
from .unified_tasks import router as unified_tasks_router

api_router = APIRouter()

api_router.include_router(blocks_router, prefix="/blocks", tags=["blocks"])
api_router.include_router(images_router, prefix="/blocks", tags=["images"])
api_router.include_router(partitions_router, prefix="/blocks", tags=["partitions"])
api_router.include_router(filesystem_router, tags=["filesystem"])
api_router.include_router(georef_router, tags=["georef"])
api_router.include_router(gpu_router, prefix="/gpu", tags=["gpu"])
api_router.include_router(tasks_router, prefix="/blocks", tags=["tasks"])
api_router.include_router(results_router, prefix="/blocks", tags=["results"])
api_router.include_router(reconstruction_router, tags=["reconstruction"])
api_router.include_router(recon_versions_router, tags=["recon-versions"])
api_router.include_router(gs_router, tags=["gs"])
api_router.include_router(gs_tiles_router, tags=["gs-tiles"])
api_router.include_router(tiles_router, tags=["tiles"])
api_router.include_router(queue_router, prefix="/queue", tags=["queue"])
api_router.include_router(system_router, prefix="", tags=["system"])
api_router.include_router(unified_tasks_router, prefix="", tags=["unified-tasks"])
