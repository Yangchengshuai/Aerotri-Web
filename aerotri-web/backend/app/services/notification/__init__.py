"""Notification service module for AeroTri Web.

This module provides a modular notification layer supporting multiple
platforms (DingTalk, Feishu, etc.) with configurable channels.

Usage:
    from app.services.notification import notification_manager, periodic_scheduler
    
    # Initialize on startup (in main.py lifespan)
    notification_manager.initialize()
    
    # Start periodic scheduler (after notification_manager is initialized)
    await periodic_scheduler.start()
    
    # Send notification (safe to call even if disabled)
    await notification_manager.notify("task_completed", {
        "block_id": "xxx",
        "block_name": "My Block",
        "duration": 3600,
    })
"""

from .manager import NotificationManager, notification_manager
from .scheduler import PeriodicScheduler, periodic_scheduler

__all__ = [
    "NotificationManager",
    "notification_manager",
    "PeriodicScheduler",
    "periodic_scheduler",
]
