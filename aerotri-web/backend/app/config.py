"""Configuration loader for AeroTri Web.

This module provides YAML configuration loading with graceful fallback.
If config files are missing or invalid, the system continues to work
with default/empty configurations.

Supports multiple image root path configurations for flexible directory browsing.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

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


# ============================================================================
# Image Root Path Configuration
# ============================================================================

class ImageRoot(BaseModel):
    """A named image root path configuration."""

    name: str = Field(description="Display name for this root path")
    path: str = Field(description="Absolute path to the root directory")

    def resolve_path(self) -> Path:
        """Resolve and validate the path."""
        resolved = Path(self.path).expanduser().resolve()
        if not resolved.exists():
            raise ValueError(f"Image root does not exist: {self.path}")
        if not resolved.is_dir():
            raise ValueError(f"Image root is not a directory: {self.path}")
        return resolved


# Global image roots cache
_image_roots: Optional[List[ImageRoot]] = None


def get_image_roots(reload: bool = False) -> List[ImageRoot]:
    """Get configured image root paths.

    Configuration priority:
    1. Config file (config/image_roots.yaml)
    2. Environment variables (AEROTRI_IMAGE_ROOTS or AEROTRI_IMAGE_ROOT)
    3. Default path (/mnt/work_odm/chengshuai)

    Args:
        reload: Force reload from disk

    Returns:
        List of ImageRoot configurations (never empty)
    """
    global _image_roots

    if not reload and _image_roots is not None:
        return _image_roots

    image_roots: List[ImageRoot] = []

    # Try loading from config file first
    try:
        image_roots = _load_image_roots_from_config()
    except Exception as e:
        logger.debug(f"No image_roots config found: {e}")

    # If no config, try environment variables
    if not image_roots:
        image_roots = _load_image_roots_from_env()

    # Ultimate fallback to default
    if not image_roots:
        default_path = os.getenv("AEROTRI_IMAGE_ROOT", "/mnt/work_odm/chengshuai")
        image_roots = [
            ImageRoot(name="默认路径", path=default_path),
        ]

    # Validate all paths exist (log warnings but don't fail)
    validated_roots = []
    for root in image_roots:
        try:
            root.resolve_path()  # Validate
            validated_roots.append(root)
        except ValueError as e:
            logger.warning(f"Invalid image root '{root.name}': {e}")

    _image_roots = validated_roots if validated_roots else image_roots
    return _image_roots


def _load_image_roots_from_config() -> List[ImageRoot]:
    """Load image roots from YAML configuration file.

    Expected format (config/image_roots.yaml):
        image_roots:
          - name: "项目数据"
            path: "/data/projects"
          - name: "外部存储"
            path: "/mnt/external"

    Returns:
        List of ImageRoot configurations
    """
    config = config_loader.load("image_roots")
    image_roots_data = config.get("image_roots", [])

    if not isinstance(image_roots_data, list):
        logger.warning("'image_roots' must be a list in configuration file")
        return []

    image_roots = []
    for item in image_roots_data:
        if not isinstance(item, dict):
            logger.warning("Each image root must be a dictionary")
            continue

        name = item.get("name", "未命名路径")
        path = item.get("path")
        if not path:
            logger.warning(f"Image root '{name}' is missing 'path' field")
            continue

        image_roots.append(ImageRoot(name=name, path=path))

    return image_roots


def _load_image_roots_from_env() -> List[ImageRoot]:
    """Load image roots from environment variables.

    Supports both AEROTRI_IMAGE_ROOTS (colon-separated) and AEROTRI_IMAGE_ROOT (single path).

    Examples:
        AEROTRI_IMAGE_ROOTS="/data/images:/mnt/storage:/home/user/images"
        AEROTRI_IMAGE_ROOT="/data/images"

    Returns:
        List of ImageRoot configurations
    """
    image_roots: List[ImageRoot] = []

    # Try AEROTRI_IMAGE_ROOTS first (colon-separated paths)
    roots_str = os.getenv("AEROTRI_IMAGE_ROOTS", "")
    if roots_str:
        paths = [p.strip() for p in roots_str.split(":") if p.strip()]
        for i, path in enumerate(paths):
            # Generate a default name based on the path
            name = f"路径 {i + 1}"
            # Use the last directory component as the name if available
            path_obj = Path(path)
            if path_obj.name and path_obj.name != path:
                name = path_obj.name
            image_roots.append(ImageRoot(name=name, path=path))
    else:
        # Fallback to AEROTRI_IMAGE_ROOT for backward compatibility
        single_path = os.getenv("AEROTRI_IMAGE_ROOT")
        if single_path:
            image_roots.append(
                ImageRoot(name="默认路径", path=single_path),
            )

    return image_roots


def get_image_root(identifier: str) -> Optional[ImageRoot]:
    """Get an image root by name or path.

    Args:
        identifier: Either the display name or the path of the root

    Returns:
        The matching ImageRoot, or None if not found
    """
    image_roots = get_image_roots()
    for root in image_roots:
        if root.name == identifier or root.path == identifier:
            return root
    return None


def reload_image_roots() -> List[ImageRoot]:
    """Force reload image root configuration.

    Useful for configuration changes without restarting the server.

    Returns:
        The newly loaded image roots
    """
    global _image_roots
    _image_roots = None
    return get_image_roots()
