"""DingTalk notification implementation."""

import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Any, Optional

import aiohttp

from .base import BaseNotifier, NotificationChannel

logger = logging.getLogger(__name__)


class DingTalkNotifier(BaseNotifier):
    """DingTalk (钉钉) notification provider."""
    
    def __init__(self):
        super().__init__("dingtalk")
    
    def _generate_sign(self, secret: str, timestamp: int) -> str:
        """Generate signature for DingTalk webhook.
        
        Args:
            secret: The secret key for signing
            timestamp: Current timestamp in milliseconds
            
        Returns:
            URL-encoded signature string
        """
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return sign
    
    def _build_webhook_url(self, channel: NotificationChannel) -> str:
        """Build the full webhook URL with signature if secret is configured.
        
        Args:
            channel: Channel configuration
            
        Returns:
            Full webhook URL
        """
        url = channel.webhook_url
        
        if channel.secret:
            timestamp = int(time.time() * 1000)
            sign = self._generate_sign(channel.secret, timestamp)
            
            # Add timestamp and sign to URL
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}timestamp={timestamp}&sign={sign}"
        
        return url
    
    async def send(
        self,
        channel: NotificationChannel,
        title: str,
        content: str,
        at_mobiles: Optional[list] = None,
        at_all: bool = False,
        **kwargs: Any,
    ) -> bool:
        """Send markdown message to DingTalk channel.
        
        Args:
            channel: Target channel configuration
            title: Message title
            content: Message content (markdown)
            at_mobiles: List of mobile numbers to @mention
            at_all: Whether to @all
            **kwargs: Additional parameters (ignored)
            
        Returns:
            True if sent successfully
        """
        if not channel.enabled:
            logger.debug(f"Channel {channel.name} is disabled, skipping")
            return False
        
        if not channel.webhook_url:
            logger.warning(f"Channel {channel.name} has no webhook URL")
            return False
        
        # Build webhook URL with signature
        url = self._build_webhook_url(channel)
        
        # Build message payload
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all,
            },
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    result = await response.json()
                    
                    if result.get("errcode") == 0:
                        logger.debug(f"DingTalk message sent to {channel.name}")
                        return True
                    else:
                        logger.warning(
                            f"DingTalk API error for {channel.name}: "
                            f"errcode={result.get('errcode')}, errmsg={result.get('errmsg')}"
                        )
                        return False
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error sending to DingTalk {channel.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to DingTalk {channel.name}: {e}")
            return False
    
    async def send_text(
        self,
        channel: NotificationChannel,
        content: str,
        at_mobiles: Optional[list] = None,
        at_all: bool = False,
    ) -> bool:
        """Send plain text message to DingTalk channel.
        
        Args:
            channel: Target channel configuration
            content: Message content (plain text)
            at_mobiles: List of mobile numbers to @mention
            at_all: Whether to @all
            
        Returns:
            True if sent successfully
        """
        if not channel.enabled or not channel.webhook_url:
            return False
        
        url = self._build_webhook_url(channel)
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all,
            },
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    result = await response.json()
                    return result.get("errcode") == 0
        except Exception as e:
            logger.error(f"Error sending text to DingTalk: {e}")
            return False
