"""Task notification helper for Runner integration.

This module provides a simple interface for sending task notifications
from various runners (task_runner, openmvs_runner, gs_runner, etc.).

Usage:
    from app.services.task_notifier import task_notifier
    
    # On task start
    await task_notifier.on_task_started(block_id, block_name, "sfm")
    
    # On task complete
    await task_notifier.on_task_completed(block_id, block_name, "sfm", duration=3600)
    
    # On task failed
    await task_notifier.on_task_failed(
        block_id, block_name, "sfm",
        error="...", stage="...", log_tail=[...]
    )
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class TaskNotifier:
    """Helper class for task notifications.
    
    Wraps notification_manager to provide a clean interface for runners.
    All methods are safe to call - they will no-op gracefully if
    notification service is not enabled.
    """
    
    def _get_manager(self):
        """Lazily get notification manager to avoid circular imports."""
        try:
            from .notification import notification_manager
            return notification_manager
        except ImportError:
            return None
    
    async def on_task_started(
        self,
        block_id: str,
        block_name: str,
        task_type: str,
    ) -> None:
        """Notify that a task has started.
        
        Args:
            block_id: Block ID
            block_name: Block name
            task_type: Task type (sfm/recon/gs/gs_tiles/tiles)
        """
        try:
            manager = self._get_manager()
            if manager and manager.enabled:
                await manager.notify_task_started(
                    block_id=block_id,
                    block_name=block_name,
                    task_type=task_type,
                )
        except Exception as e:
            logger.warning(f"Failed to send task started notification: {e}")
    
    async def on_task_completed(
        self,
        block_id: str,
        block_name: str,
        task_type: str,
        duration: Optional[float] = None,
        output_summary: Optional[str] = None,
    ) -> None:
        """Notify that a task has completed.
        
        Args:
            block_id: Block ID
            block_name: Block name
            task_type: Task type
            duration: Task duration in seconds
            output_summary: Optional summary of output
        """
        try:
            manager = self._get_manager()
            if manager and manager.enabled:
                await manager.notify_task_completed(
                    block_id=block_id,
                    block_name=block_name,
                    task_type=task_type,
                    duration=duration,
                    output_summary=output_summary,
                )
        except Exception as e:
            logger.warning(f"Failed to send task completed notification: {e}")
    
    async def on_task_failed(
        self,
        block_id: str,
        block_name: str,
        task_type: str,
        error: Optional[str] = None,
        stage: Optional[str] = None,
        duration: Optional[float] = None,
        log_tail: Optional[List[str]] = None,
    ) -> None:
        """Notify that a task has failed.
        
        Args:
            block_id: Block ID
            block_name: Block name
            task_type: Task type
            error: Error message
            stage: Current stage when failed
            duration: Task duration before failure
            log_tail: Last N lines of log
        """
        try:
            manager = self._get_manager()
            if manager and manager.enabled:
                await manager.notify_task_failed(
                    block_id=block_id,
                    block_name=block_name,
                    task_type=task_type,
                    error=error,
                    stage=stage,
                    duration=duration,
                    log_tail=log_tail,
                )
        except Exception as e:
            logger.warning(f"Failed to send task failed notification: {e}")


# Global instance
task_notifier = TaskNotifier()
