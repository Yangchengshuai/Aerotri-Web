"""Notification manager for unified notification handling."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseNotifier, NotificationChannel
from .dingtalk import DingTalkNotifier
from .templates import NotificationTemplates

logger = logging.getLogger(__name__)


class NotificationManager:
    """Unified notification manager.
    
    Manages multiple notification providers and routes events to appropriate channels.
    Designed to be safe to call even when disabled - all methods gracefully no-op.
    """
    
    def __init__(self):
        self._enabled = False
        self._initialized = False
        self._config: Dict[str, Any] = {}
        self._notifiers: Dict[str, BaseNotifier] = {}
        self._startup_time: Optional[datetime] = None
    
    @property
    def enabled(self) -> bool:
        """Check if notification service is enabled."""
        return self._enabled
    
    @property
    def initialized(self) -> bool:
        """Check if notification service is initialized."""
        return self._initialized
    
    def initialize(self, config_path: Optional[str] = None) -> bool:
        """Initialize notification service from config file.
        
        Args:
            config_path: Path to notification.yaml config file.
                        If None, uses default path.
                        
        Returns:
            True if initialized and enabled, False otherwise
        """
        if self._initialized:
            logger.debug("NotificationManager already initialized")
            return self._enabled
        
        self._startup_time = datetime.utcnow()
        
        # Determine config path
        if config_path is None:
            # Default path: backend/config/notification.yaml
            config_path = str(
                Path(__file__).parent.parent.parent.parent / "config" / "notification.yaml"
            )
        
        config_file = Path(config_path)
        
        # Check if config exists
        if not config_file.exists():
            logger.info(f"Notification config not found at {config_path}, service disabled")
            self._initialized = True
            self._enabled = False
            return False
        
        # Load config
        try:
            from ...config import config_loader
            self._config = config_loader.load("notification")
        except Exception as e:
            logger.warning(f"Failed to load notification config: {e}")
            self._initialized = True
            self._enabled = False
            return False
        
        # Check global enable flag
        notification_config = self._config.get("notification", {})
        if not notification_config.get("enabled", False):
            logger.info("Notification service disabled by config")
            self._initialized = True
            self._enabled = False
            return False
        
        # Initialize notifiers
        self._init_dingtalk(notification_config.get("dingtalk", {}))
        # Future: self._init_feishu(notification_config.get("feishu", {}))
        
        # Check if any notifier is configured
        has_notifier = any(n.is_configured() for n in self._notifiers.values())
        if not has_notifier:
            logger.warning("No notification channels configured, service disabled")
            self._initialized = True
            self._enabled = False
            return False
        
        self._initialized = True
        self._enabled = True
        logger.info("NotificationManager initialized successfully")
        return True
    
    def _init_dingtalk(self, config: Dict[str, Any]) -> None:
        """Initialize DingTalk notifier from config."""
        channels_config = config.get("channels", {})
        if not channels_config:
            return
        
        notifier = DingTalkNotifier()
        
        for name, ch_config in channels_config.items():
            if not isinstance(ch_config, dict):
                continue
            
            channel = NotificationChannel(
                name=name,
                enabled=ch_config.get("enabled", False),
                webhook_url=ch_config.get("webhook_url", ""),
                secret=ch_config.get("secret"),
                events=ch_config.get("events", []),
            )
            notifier.add_channel(channel)
            logger.debug(f"Added DingTalk channel: {name}")
        
        if notifier.is_configured():
            self._notifiers["dingtalk"] = notifier
            logger.info(f"DingTalk notifier configured with {len(notifier.channels)} channels")
    
    async def notify(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> int:
        """Send notification for an event.
        
        This method is safe to call even if the service is disabled.
        It will gracefully no-op and return 0.
        
        Args:
            event_type: Type of event (e.g., "task_completed", "backend_startup")
            data: Event data dictionary
            **kwargs: Additional parameters passed to template
            
        Returns:
            Number of channels successfully notified
        """
        if not self._enabled:
            return 0
        
        if data is None:
            data = {}
        
        # Merge kwargs into data
        merged_data = {**data, **kwargs}
        
        # Generate message from template
        title, content = self._get_message(event_type, merged_data)
        if not title or not content:
            logger.warning(f"No template found for event: {event_type}")
            return 0
        
        # Send to all configured notifiers
        total_sent = 0
        for notifier in self._notifiers.values():
            try:
                sent = await notifier.notify(event_type, title, content, **merged_data)
                total_sent += sent
            except Exception as e:
                logger.error(f"Error in notifier {notifier.name}: {e}")
        
        return total_sent
    
    def _get_message(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> tuple:
        """Get title and content for an event type.
        
        Args:
            event_type: Type of event
            data: Event data
            
        Returns:
            Tuple of (title, content), or (None, None) if no template
        """
        templates = NotificationTemplates()
        
        # Map event types to template methods
        template_map = {
            "task_started": templates.task_started,
            "task_completed": templates.task_completed,
            "task_failed": templates.task_failed,
            "backend_startup": templates.backend_startup,
            "backend_shutdown": templates.backend_shutdown,
            "backend_error": templates.backend_error,
            "system_status": templates.system_status,
            "periodic_task_summary": templates.periodic_task_summary,
        }
        
        template_func = template_map.get(event_type)
        if template_func is None:
            return None, None
        
        try:
            return template_func(**data)
        except Exception as e:
            logger.error(f"Error generating template for {event_type}: {e}")
            return None, None
    
    async def notify_task_started(
        self,
        block_id: str,
        block_name: str,
        task_type: str,
        **kwargs: Any,
    ) -> int:
        """Convenience method for task started notification."""
        return await self.notify("task_started", {
            "block_id": block_id,
            "block_name": block_name,
            "task_type": task_type,
            "started_at": datetime.utcnow(),
            **kwargs,
        })
    
    async def notify_task_completed(
        self,
        block_id: str,
        block_name: str,
        task_type: str,
        duration: Optional[float] = None,
        **kwargs: Any,
    ) -> int:
        """Convenience method for task completed notification."""
        return await self.notify("task_completed", {
            "block_id": block_id,
            "block_name": block_name,
            "task_type": task_type,
            "duration": duration,
            **kwargs,
        })
    
    async def notify_task_failed(
        self,
        block_id: str,
        block_name: str,
        task_type: str,
        error: Optional[str] = None,
        stage: Optional[str] = None,
        duration: Optional[float] = None,
        log_tail: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> int:
        """Convenience method for task failed notification."""
        return await self.notify("task_failed", {
            "block_id": block_id,
            "block_name": block_name,
            "task_type": task_type,
            "error": error,
            "stage": stage,
            "duration": duration,
            "log_tail": log_tail,
            **kwargs,
        })
    
    async def notify_backend_startup(self, version: str = "1.0.0") -> int:
        """Convenience method for backend startup notification."""
        return await self.notify("backend_startup", {
            "version": version,
            "started_at": self._startup_time or datetime.utcnow(),
        })
    
    async def notify_backend_shutdown(self) -> int:
        """Convenience method for backend shutdown notification."""
        uptime = None
        if self._startup_time:
            uptime = (datetime.utcnow() - self._startup_time).total_seconds()
        
        return await self.notify("backend_shutdown", {
            "uptime": uptime,
            "shutdown_at": datetime.utcnow(),
        })
    
    def get_uptime(self) -> Optional[float]:
        """Get service uptime in seconds."""
        if self._startup_time:
            return (datetime.utcnow() - self._startup_time).total_seconds()
        return None


# Global notification manager instance
notification_manager = NotificationManager()
