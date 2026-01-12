# Lazy imports to avoid circular dependencies and early pynvml crashes
# Direct imports are only done when explicitly needed

def __getattr__(name):
    """Lazy import services to avoid early initialization issues."""
    if name == "ImageService":
        from .image_service import ImageService
        return ImageService
    elif name == "GPUService":
        from .gpu_service import GPUService
        return GPUService
    elif name == "TaskRunner":
        from .task_runner import TaskRunner
        return TaskRunner
    elif name == "LogParser":
        from .log_parser import LogParser
        return LogParser
    elif name == "ResultReader":
        from .result_reader import ResultReader
        return ResultReader
    elif name == "WorkspaceService":
        from .workspace_service import WorkspaceService
        return WorkspaceService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ImageService",
    "GPUService", 
    "TaskRunner",
    "LogParser",
    "ResultReader",
    "WorkspaceService",
]
