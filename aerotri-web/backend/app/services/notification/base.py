"""Base classes for notification service."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationChannel:
    """Represents a notification channel configuration."""
    
    def __init__(
        self,
        name: str,
        enabled: bool,
        webhook_url: str,
        secret: Optional[str] = None,
        events: Optional[List[str]] = None,
    ):
        self.name = name
        self.enabled = enabled
        self.webhook_url = webhook_url
        self.secret = secret
        self.events = events or []
    
    def handles_event(self, event_type: str) -> bool:
        """Check if this channel handles the given event type."""
        if not self.enabled:
            return False
        if not self.events:
            # No events specified = handle all events
            return True
        return event_type in self.events
    
    def __repr__(self) -> str:
        return f"NotificationChannel(name={self.name}, enabled={self.enabled}, events={self.events})"


class BaseNotifier(ABC):
    """Abstract base class for notification providers."""
    
    def __init__(self, name: str):
        self.name = name
        self.channels: Dict[str, NotificationChannel] = {}
        self._initialized = False
    
    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self.channels[channel.name] = channel
        logger.debug(f"Added channel {channel.name} to {self.name}")
    
    def get_channels_for_event(self, event_type: str) -> List[NotificationChannel]:
        """Get all channels that handle the given event type."""
        return [
            ch for ch in self.channels.values()
            if ch.handles_event(event_type)
        ]
    
    @abstractmethod
    async def send(
        self,
        channel: NotificationChannel,
        title: str,
        content: str,
        **kwargs: Any,
    ) -> bool:
        """Send a notification to a specific channel.
        
        Args:
            channel: Target channel configuration
            title: Notification title
            content: Notification content (markdown supported)
            **kwargs: Additional platform-specific parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    async def notify(
        self,
        event_type: str,
        title: str,
        content: str,
        **kwargs: Any,
    ) -> int:
        """Send notification to all channels that handle this event type.
        
        Args:
            event_type: Type of event (e.g., "task_completed")
            title: Notification title
            content: Notification content
            **kwargs: Additional parameters
            
        Returns:
            Number of channels successfully notified
        """
        channels = self.get_channels_for_event(event_type)
        if not channels:
            logger.debug(f"No channels configured for event: {event_type}")
            return 0
        
        success_count = 0
        for channel in channels:
            try:
                result = await self.send(channel, title, content, **kwargs)
                if result:
                    success_count += 1
                    logger.info(f"Notification sent to {self.name}/{channel.name}: {title}")
                else:
                    logger.warning(f"Failed to send notification to {self.name}/{channel.name}")
            except Exception as e:
                logger.error(f"Error sending notification to {self.name}/{channel.name}: {e}")
        
        return success_count
    
    def is_configured(self) -> bool:
        """Check if this notifier has any enabled channels."""
        return any(ch.enabled for ch in self.channels.values())
