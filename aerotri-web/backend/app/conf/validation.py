"""配置验证工具

提供启动时配置验证功能，确保关键配置正确且可用。
"""
import os
import logging
from pathlib import Path
from typing import List, Tuple

from .settings import get_settings
from app.config import get_image_roots

logger = logging.getLogger(__name__)


def validate_on_startup() -> List[str]:
    """
    启动时验证配置

    验证项目:
    1. 创建必要的目录
    2. 验证数据库路径可写
    3. 验证图像根路径
    4. 验证关键可执行文件（警告不阻塞）

    Returns:
        警告列表（错误会抛出异常）
    """
    settings = get_settings()
    errors: List[str] = []
    warnings: List[str] = []

    # 1. 创建必要的目录
    try:
        settings.setup_directories()
        logger.info(f"Directories created successfully: data_dir={settings.paths.data_dir}")
    except Exception as e:
        error_msg = f"Failed to create directories: {e}"
        errors.append(error_msg)
        logger.error(error_msg)

    # 2. 验证数据库路径可写
    try:
        db_path = settings.database.path
        # 确保数据库目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # 尝试创建/打开数据库文件以验证可写性
        if db_path.exists():
            # 文件已存在，检查是否可读
            if not db_path.is_file():
                errors.append(f"Database path exists but is not a file: {db_path}")
            else:
                logger.debug(f"Database file exists: {db_path}")
        else:
            # 文件不存在，尝试创建空文件验证可写性
            try:
                db_path.touch()
                db_path.unlink()  # 删除测试文件
                logger.debug(f"Database path is writable: {db_path}")
            except Exception as e:
                errors.append(f"Database path is not writable: {db_path} - {e}")
    except Exception as e:
        errors.append(f"Database validation failed: {e}")

    # 3. 验证图像根路径
    try:
        roots = get_image_roots()
        if not roots:
            warnings.append("No valid image roots configured. Users will not be able to browse images.")
            logger.warning("No valid image roots configured")
        else:
            logger.info(f"Found {len(roots)} valid image root(s)")
            for root in roots:
                logger.debug(f"  - {root.name}: {root.path}")
    except Exception as e:
        warnings.append(f"Image roots validation failed: {e}")
        logger.warning(f"Image roots validation failed: {e}")

    # 4. 验证关键可执行文件（警告不阻塞）
    missing = settings.validate_executables()
    if missing:
        for category, items in missing.items():
            warnings.append(f"Missing {category} executable(s): {', '.join(items)}")
            logger.warning(f"Missing {category} executables: {items}")

    # 5. 验证路径配置
    try:
        project_root = settings.paths.project_root
        if project_root and not project_root.exists():
            errors.append(f"Project root does not exist: {project_root}")
        else:
            logger.debug(f"Project root: {project_root}")
    except Exception as e:
        warnings.append(f"Project root validation warning: {e}")

    # 汇总结果
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")

    logger.info("Configuration validated successfully")

    # 记录配置摘要
    _log_config_summary(settings)

    return warnings


def _log_config_summary(settings) -> None:
    """
    记录配置摘要信息

    Args:
        settings: AppSettings 配置实例
    """
    logger.info("=" * 60)
    logger.info("Configuration Summary")
    logger.info("=" * 60)

    # 基本信息
    logger.info(f"Application: {settings.name} v{settings.version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")

    # 路径配置
    logger.info(f"Project Root: {settings.paths.project_root}")
    logger.info(f"Database Path: {settings.database.path}")
    logger.info(f"Outputs Directory: {settings.paths.outputs_dir}")
    logger.info(f"Blocks Directory: {settings.paths.blocks_dir}")
    logger.info(f"Thumbnails Directory: {settings.paths.thumbnails_dir}")

    # 算法配置
    logger.info("Algorithm Paths:")
    logger.info(f"  - COLMAP: {settings.algorithms.colmap.path}")
    logger.info(f"  - GLOMAP: {settings.algorithms.glomap.path}")
    logger.info(f"  - InstantSfM: {settings.algorithms.instantsfm.path}")
    logger.info(f"  - OpenMVG: {settings.algorithms.openmvg.bin_dir}")
    logger.info(f"  - OpenMVS: {settings.algorithms.openmvs.bin_dir}")

    # 3DGS 配置
    logger.info(f"3DGS Repository: {settings.gaussian_splatting.repo_path}")
    logger.info(f"3DGS Python: {settings.gaussian_splatting.python}")

    # 队列配置
    logger.info(f"Queue Max Concurrent: {settings.queue.max_concurrent}")

    # GPU 配置
    logger.info(f"GPU Monitor Interval: {settings.gpu.monitor_interval}s")
    logger.info(f"GPU Auto Selection: {settings.gpu.auto_selection}")

    logger.info("=" * 60)


def validate_path_exists(path: Path, path_type: str = "path") -> Tuple[bool, str]:
    """
    验证路径是否存在

    Args:
        path: 要验证的路径
        path_type: 路径类型描述（如 "executable", "directory"）

    Returns:
        (is_valid, message) - 是否有效及详细消息
    """
    if not path.exists():
        return False, f"{path_type} does not exist: {path}"

    if path.is_file() and not os.access(path, os.X_OK):
        return False, f"{path_type} is not executable: {path}"

    if path.is_dir() and not os.access(path, os.R_OK):
        return False, f"{path_type} is not readable: {path}"

    return True, f"{path_type} is valid: {path}"


def validate_disk_space(path: Path, min_space_gb: float = 10.0) -> Tuple[bool, str]:
    """
    验证磁盘空间是否足够

    Args:
        path: 要检查的路径
        min_space_gb: 最小所需空间（GB）

    Returns:
        (is_valid, message) - 是否有效及详细消息
    """
    import shutil

    try:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024 ** 3)

        if free_gb < min_space_gb:
            return False, f"Low disk space: {free_gb:.2f}GB free (recommended {min_space_gb}GB)"

        return True, f"Sufficient disk space: {free_gb:.2f}GB free"
    except Exception as e:
        return False, f"Failed to check disk space: {e}"
