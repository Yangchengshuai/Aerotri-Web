"""System monitoring service for AeroTri Web.

Provides CPU, memory, disk, and GPU monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)

# Lazy GPU imports to avoid segfault on systems without proper GPU drivers
_gpu_service_loaded = False
_GPUService = None


def _get_gpu_service():
    """Lazily load GPUService to avoid import-time issues."""
    global _gpu_service_loaded, _GPUService
    if not _gpu_service_loaded:
        try:
            from .gpu_service import GPUService
            _GPUService = GPUService
        except Exception as e:
            logger.warning(f"Failed to load GPUService: {e}")
            _GPUService = None
        _gpu_service_loaded = True
    return _GPUService


class SystemMonitor:
    """System resource monitor."""
    
    @staticmethod
    def get_cpu_percent(interval: float = 0.1) -> float:
        """Get CPU usage percentage.
        
        Args:
            interval: Measurement interval in seconds
            
        Returns:
            CPU usage percentage (0-100)
        """
        try:
            return psutil.cpu_percent(interval=interval)
        except Exception as e:
            logger.warning(f"Failed to get CPU percent: {e}")
            return 0.0
    
    @staticmethod
    def get_memory_info() -> dict:
        """Get memory usage information.
        
        Returns:
            Dict with total_gb, used_gb, available_gb, percent
        """
        try:
            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024 ** 3), 2),
                "used_gb": round(mem.used / (1024 ** 3), 2),
                "available_gb": round(mem.available / (1024 ** 3), 2),
                "percent": mem.percent,
            }
        except Exception as e:
            logger.warning(f"Failed to get memory info: {e}")
            return {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "available_gb": 0.0,
                "percent": 0.0,
            }
    
    @staticmethod
    def get_disk_info(path: str = "/") -> dict:
        """Get disk usage information for a given path.
        
        Args:
            path: Filesystem path to check (default: root)
            
        Returns:
            Dict with total_gb, used_gb, free_gb, percent
        """
        try:
            disk = psutil.disk_usage(path)
            return {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "percent": disk.percent,
            }
        except Exception as e:
            logger.warning(f"Failed to get disk info for {path}: {e}")
            return {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "percent": 0.0,
            }
    
    @staticmethod
    def get_gpu_info() -> List:
        """Get GPU information.
        
        Returns:
            List of GPUInfo-like objects (dicts or GPUInfo instances)
        """
        try:
            GPUService = _get_gpu_service()
            if GPUService is None:
                return []
            return GPUService.get_all_gpus()
        except Exception as e:
            logger.warning(f"Failed to get GPU info: {e}")
            return []
    
    @classmethod
    def get_system_status(cls) -> dict:
        """Get complete system status snapshot.
        
        Returns:
            Dict with all system metrics
        """
        memory = cls.get_memory_info()
        disk = cls.get_disk_info("/")
        gpus = cls.get_gpu_info()
        
        return {
            "cpu_percent": cls.get_cpu_percent(),
            "memory_total_gb": memory["total_gb"],
            "memory_used_gb": memory["used_gb"],
            "memory_available_gb": memory["available_gb"],
            "memory_percent": memory["percent"],
            "disk_total_gb": disk["total_gb"],
            "disk_used_gb": disk["used_gb"],
            "disk_free_gb": disk["free_gb"],
            "disk_percent": disk["percent"],
            "gpus": [gpu.model_dump() if hasattr(gpu, 'model_dump') else gpu.dict() for gpu in gpus],
            "gpu_count": len(gpus),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global instance
system_monitor = SystemMonitor()
