"""GPU monitoring service."""
from typing import List, Optional

# Lazy import to avoid crashes on systems without proper GPU drivers
PYNVML_AVAILABLE = None  # None = not checked yet, True/False = checked
_pynvml = None


def _ensure_pynvml():
    """Lazily import and check pynvml availability."""
    global PYNVML_AVAILABLE, _pynvml
    if PYNVML_AVAILABLE is None:
        try:
            import pynvml
            _pynvml = pynvml
            PYNVML_AVAILABLE = True
        except ImportError:
            PYNVML_AVAILABLE = False
        except Exception:
            PYNVML_AVAILABLE = False
    return PYNVML_AVAILABLE, _pynvml


def _get_gpu_info_schema():
    """Lazily import GPUInfo schema."""
    from ..schemas import GPUInfo
    return GPUInfo


class GPUService:
    """Service for GPU monitoring."""
    
    _initialized = False
    
    @classmethod
    def _ensure_initialized(cls):
        """Ensure pynvml is initialized."""
        available, pynvml = _ensure_pynvml()
        if not available or pynvml is None:
            return False
        
        if not cls._initialized:
            try:
                pynvml.nvmlInit()
                cls._initialized = True
            except Exception:
                return False
        return True
    
    @classmethod
    def get_gpu_count(cls) -> int:
        """Get number of available GPUs."""
        if not cls._ensure_initialized():
            return 0
        
        try:
            _, pynvml = _ensure_pynvml()
            return pynvml.nvmlDeviceGetCount()
        except Exception:
            return 0
    
    @classmethod
    def get_gpu(cls, index: int) -> Optional["GPUInfo"]:
        """Get information about a specific GPU.
        
        Args:
            index: GPU index
            
        Returns:
            GPUInfo or None if not available
        """
        if not cls._ensure_initialized():
            return None
        
        try:
            _, pynvml = _ensure_pynvml()
            GPUInfo = _get_gpu_info_schema()
            
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            
            # Get name
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            
            # Get memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            memory_total = mem_info.total // (1024 * 1024)  # Convert to MB
            memory_used = mem_info.used // (1024 * 1024)
            memory_free = mem_info.free // (1024 * 1024)
            
            # Get utilization
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                utilization = util.gpu
            except Exception:
                utilization = 0
            
            # Determine availability (free memory > 1GB and utilization < 90%)
            is_available = memory_free > 1024 and utilization < 90
            
            return GPUInfo(
                index=index,
                name=name,
                memory_total=memory_total,
                memory_used=memory_used,
                memory_free=memory_free,
                utilization=utilization,
                is_available=is_available
            )
        except Exception as e:
            return None
    
    @classmethod
    def get_all_gpus(cls) -> List:
        """Get information about all GPUs.
        
        Returns:
            List of GPUInfo
        """
        gpus = []
        count = cls.get_gpu_count()
        
        for i in range(count):
            gpu = cls.get_gpu(i)
            if gpu:
                gpus.append(gpu)
        
        return gpus
    
    @classmethod
    def is_gpu_available(cls, index: int) -> bool:
        """Check if a GPU is available for use.
        
        Args:
            index: GPU index
            
        Returns:
            True if available
        """
        gpu = cls.get_gpu(index)
        return gpu is not None and gpu.is_available
