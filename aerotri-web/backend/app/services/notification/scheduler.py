"""Periodic notification scheduler.

This module provides a scheduler for sending periodic notifications
such as system status summaries and task reports.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PeriodicScheduler:
    """Scheduler for periodic notification tasks.
    
    Supports:
    - Interval-based scheduling (e.g., every 4 hours)
    - Cron-like scheduling (e.g., daily at 21:00)
    """
    
    def __init__(self):
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._config: Dict[str, Any] = {}
    
    @property
    def running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the scheduler from notification config.
        
        Args:
            config: The 'periodic' section of notification config
        """
        self._config = config or {}
        logger.debug(f"PeriodicScheduler configured: {self._config}")
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.debug("PeriodicScheduler already running")
            return
        
        self._running = True
        logger.info("PeriodicScheduler starting...")
        
        # Start system status periodic task
        system_status_config = self._config.get("system_status", {})
        if system_status_config.get("enabled", False):
            interval = system_status_config.get("interval", 14400)  # Default 4 hours
            self._tasks["system_status"] = asyncio.create_task(
                self._run_interval_task("system_status", interval)
            )
            logger.info(f"System status periodic task started (interval: {interval}s)")
        
        # Start task summary periodic task
        task_summary_config = self._config.get("task_summary", {})
        if task_summary_config.get("enabled", False):
            cron = task_summary_config.get("cron", "0 21 * * *")
            self._tasks["task_summary"] = asyncio.create_task(
                self._run_cron_task("task_summary", cron)
            )
            logger.info(f"Task summary periodic task started (cron: {cron})")
        
        logger.info("PeriodicScheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all tasks
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.debug(f"Cancelled periodic task: {name}")
        
        self._tasks.clear()
        logger.info("PeriodicScheduler stopped")
    
    async def _run_interval_task(self, task_name: str, interval: int) -> None:
        """Run a task at regular intervals.
        
        Args:
            task_name: Name of the task (e.g., "system_status")
            interval: Interval in seconds
        """
        logger.debug(f"Starting interval task '{task_name}' with interval {interval}s")
        
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                if not self._running:
                    break
                
                await self._execute_task(task_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in interval task '{task_name}': {e}")
                # Continue running even if one execution fails
                await asyncio.sleep(60)  # Wait a bit before retrying
    
    async def _run_cron_task(self, task_name: str, cron_expr: str) -> None:
        """Run a task based on cron expression.
        
        Simplified cron implementation supporting: minute hour day month weekday
        
        Args:
            task_name: Name of the task
            cron_expr: Cron expression (e.g., "0 21 * * *" for daily at 21:00)
        """
        logger.debug(f"Starting cron task '{task_name}' with expression '{cron_expr}'")
        
        while self._running:
            try:
                # Calculate seconds until next execution
                seconds_until_next = self._get_seconds_until_cron(cron_expr)
                
                if seconds_until_next is None:
                    logger.warning(f"Invalid cron expression: {cron_expr}")
                    await asyncio.sleep(3600)  # Wait an hour and retry
                    continue
                
                logger.debug(f"Cron task '{task_name}' next execution in {seconds_until_next}s")
                
                await asyncio.sleep(seconds_until_next)
                
                if not self._running:
                    break
                
                await self._execute_task(task_name)
                
                # Sleep a bit to avoid re-triggering in the same minute
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cron task '{task_name}': {e}")
                await asyncio.sleep(60)
    
    def _get_seconds_until_cron(self, cron_expr: str) -> Optional[int]:
        """Calculate seconds until the next cron execution.
        
        Simplified implementation - only supports: minute hour * * *
        
        Args:
            cron_expr: Cron expression
            
        Returns:
            Seconds until next execution, or None if invalid
        """
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return None
            
            minute = int(parts[0]) if parts[0] != "*" else None
            hour = int(parts[1]) if parts[1] != "*" else None
            
            now = datetime.now()
            
            # Simple case: specific hour and minute
            if hour is not None and minute is not None:
                # Calculate target time today
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If target is in the past, move to tomorrow
                if target <= now:
                    target = target.replace(day=target.day + 1)
                
                return int((target - now).total_seconds())
            
            # If only minute specified, run every hour at that minute
            if hour is None and minute is not None:
                target = now.replace(minute=minute, second=0, microsecond=0)
                if target <= now:
                    # Move to next hour
                    target = target.replace(hour=(target.hour + 1) % 24)
                    if target.hour == 0:
                        target = target.replace(day=target.day + 1)
                return int((target - now).total_seconds())
            
            # Default: run in 1 hour
            return 3600
            
        except Exception as e:
            logger.warning(f"Failed to parse cron expression '{cron_expr}': {e}")
            return None
    
    async def _execute_task(self, task_name: str) -> None:
        """Execute a periodic task.
        
        Args:
            task_name: Name of the task to execute
        """
        try:
            logger.info(f"Executing periodic task: {task_name}")
            
            if task_name == "system_status":
                await self._send_system_status()
            elif task_name == "task_summary":
                await self._send_task_summary()
            else:
                logger.warning(f"Unknown task: {task_name}")
                
        except Exception as e:
            logger.error(f"Failed to execute task '{task_name}': {e}")
    
    async def _send_system_status(self) -> None:
        """Send system status notification."""
        try:
            from ..system_monitor import system_monitor
            from ..task_view_service import task_view_service
            from ...models.database import AsyncSessionLocal
            from . import notification_manager
            
            # Get system status
            status = system_monitor.get_system_status()
            
            # Get task counts
            async with AsyncSessionLocal() as db:
                summary = await task_view_service.get_task_summary(db)
            
            # Send notification
            await notification_manager.notify(
                "system_status",
                {
                    "cpu_percent": status.get("cpu_percent", 0),
                    "memory_percent": status.get("memory_percent", 0),
                    "disk_percent": status.get("disk_percent", 0),
                    "gpu_info": status.get("gpus", []),
                    "running_tasks": summary.get("running", 0),
                    "queued_tasks": summary.get("waiting", 0),
                }
            )
            
            logger.info("System status notification sent")
            
        except Exception as e:
            logger.error(f"Failed to send system status: {e}")
    
    async def _send_task_summary(self) -> None:
        """Send task summary notification."""
        try:
            from ..task_view_service import task_view_service
            from ...models.database import AsyncSessionLocal
            from . import notification_manager
            
            # Get task summary
            async with AsyncSessionLocal() as db:
                summary = await task_view_service.get_task_summary(db)
            
            # For today's stats, we'd need to track this separately
            # For now, use the totals
            await notification_manager.notify(
                "periodic_task_summary",
                {
                    "running_tasks": summary.get("running", 0),
                    "queued_tasks": summary.get("waiting", 0),
                    "completed_today": summary.get("by_status", {}).get("success", 0),
                    "failed_today": summary.get("by_status", {}).get("failed", 0),
                }
            )
            
            logger.info("Task summary notification sent")
            
        except Exception as e:
            logger.error(f"Failed to send task summary: {e}")
    
    async def trigger_system_status(self) -> None:
        """Manually trigger a system status notification."""
        await self._send_system_status()
    
    async def trigger_task_summary(self) -> None:
        """Manually trigger a task summary notification."""
        await self._send_task_summary()


# Global scheduler instance
periodic_scheduler = PeriodicScheduler()
