"""Configuration loader for AeroTri Web.

This module provides YAML configuration loading with graceful fallback.
If config files are missing or invalid, the system continues to work
with default/empty configurations.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# Default config directory (relative to backend root)
CONFIG_DIR = Path(__file__).parent.parent / "config"


class ConfigLoader:
    """YAML configuration loader with caching and graceful fallback."""
    
    _instance: Optional["ConfigLoader"] = None
    _configs: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls) -> "ConfigLoader":
        """Singleton pattern to ensure single config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configs = {}
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "ConfigLoader":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load(self, name: str, reload: bool = False) -> Dict[str, Any]:
        """Load a YAML configuration file.
        
        Args:
            name: Config name (without .yaml extension), e.g., "notification"
            reload: Force reload from disk even if cached
            
        Returns:
            Configuration dict, or empty dict if file doesn't exist or is invalid
        """
        if not reload and name in self._configs:
            return self._configs[name]
        
        config = self._load_from_file(name)
        self._configs[name] = config
        return config
    
    def _load_from_file(self, name: str) -> Dict[str, Any]:
        """Load config from YAML file."""
        # Check for config file in order of priority
        config_paths = [
            CONFIG_DIR / f"{name}.yaml",
            CONFIG_DIR / f"{name}.yml",
            # Also check environment variable for custom config path
            Path(os.environ.get(f"AEROTRI_{name.upper()}_CONFIG", "")),
        ]
        
        for config_path in config_paths:
            if config_path and config_path.exists() and config_path.is_file():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f)
                        if config is None:
                            config = {}
                        logger.info(f"Loaded config '{name}' from {config_path}")
                        return config
                except yaml.YAMLError as e:
                    logger.warning(f"Failed to parse config '{name}' from {config_path}: {e}")
                    return {}
                except Exception as e:
                    logger.warning(f"Failed to load config '{name}' from {config_path}: {e}")
                    return {}
        
        # Config file not found - this is OK, return empty config
        logger.debug(f"Config '{name}' not found, using empty config")
        return {}
    
    def get(self, name: str, key: str, default: Any = None) -> Any:
        """Get a specific key from a config.
        
        Args:
            name: Config name
            key: Dot-separated key path, e.g., "notification.enabled"
            default: Default value if key not found
            
        Returns:
            Config value or default
        """
        config = self.load(name)
        
        # Navigate nested keys
        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def reload(self, name: str) -> Dict[str, Any]:
        """Force reload a config from disk.
        
        Args:
            name: Config name
            
        Returns:
            Reloaded configuration dict
        """
        return self.load(name, reload=True)
    
    def reload_all(self) -> None:
        """Reload all loaded configs from disk."""
        for name in list(self._configs.keys()):
            self.reload(name)
    
    def clear_cache(self) -> None:
        """Clear all cached configs."""
        self._configs.clear()


# Global config loader instance
config_loader = ConfigLoader.get_instance()


def get_config(name: str) -> Dict[str, Any]:
    """Convenience function to get a config by name.
    
    Args:
        name: Config name (without .yaml extension)
        
    Returns:
        Configuration dict
    """
    return config_loader.load(name)


def get_notification_config() -> Dict[str, Any]:
    """Get the notification config.
    
    Returns:
        Notification configuration dict
    """
    return config_loader.load("notification")


def is_notification_enabled() -> bool:
    """Check if notification service is enabled.
    
    Returns:
        True if notification.enabled is True in config
    """
    config = get_notification_config()
    return config.get("notification", {}).get("enabled", False)
