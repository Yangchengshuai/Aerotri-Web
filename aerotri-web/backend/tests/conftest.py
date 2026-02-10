"""
Pytest configuration and shared fixtures

这个文件包含 pytest 的全局配置和共享的测试 fixtures。
pytest 会自动发现 conftest.py 中的 fixtures。
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import yaml


@pytest.fixture
def temp_config_dir():
    """临时配置目录，用于隔离测试

    Returns:
        Path: 临时目录路径，测试结束后自动删除
    """
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_defaults_yaml(temp_config_dir):
    """创建测试用的 defaults.yaml

    创建一个最小化的默认配置文件，包含应用基本设置、路径配置和算法配置。

    Args:
        temp_config_dir: 由 temp_config_dir fixture 提供的临时目录

    Returns:
        Path: 创建的 defaults.yaml 文件路径
    """
    defaults = {
        "app": {
            "name": "AeroTri-Web",
            "debug": False
        },
        "paths": {
            "project_root": "..",
            "data_dir": "./data",
            "outputs_dir": "./data/outputs"
        },
        "algorithms": {
            "colmap": {
                "path": "colmap"
            },
            "glomap": {
                "path": "glomap"
            }
        }
    }

    defaults_path = temp_config_dir / "defaults.yaml"
    with open(defaults_path, "w", encoding='utf-8') as f:
        yaml.dump(defaults, f, allow_unicode=True)

    return defaults_path


@pytest.fixture
def mock_settings_yaml(temp_config_dir):
    """创建测试用的 settings.yaml

    创建一个覆盖部分默认值的环境特定配置文件。

    Args:
        temp_config_dir: 由 temp_config_dir fixture 提供的临时目录

    Returns:
        Path: 创建的 settings.yaml 文件路径
    """
    settings = {
        "app": {
            "debug": True,
            "environment": "testing"
        },
        "database": {
            "path": "./data/test.db"
        }
    }

    settings_path = temp_config_dir / "settings.yaml"
    with open(settings_path, "w", encoding='utf-8') as f:
        yaml.dump(settings, f, allow_unicode=True)

    return settings_path


@pytest.fixture
def mock_project_root():
    """创建测试用的项目根目录

    创建一个临时目录作为模拟的项目根目录，用于测试路径解析。

    Returns:
        Path: 临时项目根目录路径
    """
    temp_dir = Path(tempfile.mkdtemp())
    # 创建一些标准目录结构
    (temp_dir / "data").mkdir()
    (temp_dir / "data" / "outputs").mkdir()
    (temp_dir / "backend").mkdir()

    yield temp_dir

    shutil.rmtree(temp_dir)


@pytest.fixture
def full_config_dir(temp_config_dir):
    """创建完整的测试配置目录

    创建包含所有配置文件的完整测试环境。

    Args:
        temp_config_dir: 由 temp_config_dir fixture 提供的临时目录

    Returns:
        Path: 配置目录路径
    """
    # defaults.yaml
    defaults = {
        "app": {
            "name": "AeroTri-Web",
            "version": "1.0.0",
            "debug": False,
            "environment": "production"
        },
        "paths": {
            "project_root": "..",
            "data_dir": "./data",
            "outputs_dir": "./data/outputs",
            "blocks_dir": "./data/blocks",
            "thumbnails_dir": "./data/thumbnails"
        },
        "database": {
            "path": "./data/aerotri.db",
            "pool_size": 5,
            "max_overflow": 10
        },
        "algorithms": {
            "colmap": {
                "path": "colmap"
            },
            "glomap": {
                "path": "glomap"
            },
            "instantsfm": {
                "path": "ins-sfm"
            },
            "openmvg": {
                "bin_dir": "/usr/local/bin",
                "sensor_db": "/usr/local/share/sensor_db.txt"
            },
            "openmvs": {
                "bin_dir": "/usr/local/lib/openmvs/bin"
            }
        },
        "gaussian_splatting": {
            "repo_path": "/opt/gaussian-splatting",
            "python": "python",
            "tensorboard_path": "tensorboard",
            "tensorboard_port_start": 6006,
            "tensorboard_port_end": 6100
        },
        "queue": {
            "max_concurrent": 1,
            "retry_failed_tasks": False,
            "retry_delay_seconds": 60
        }
    }

    defaults_path = temp_config_dir / "defaults.yaml"
    with open(defaults_path, "w", encoding='utf-8') as f:
        yaml.dump(defaults, f, allow_unicode=True)

    # settings.yaml (development override)
    settings = {
        "app": {
            "debug": True,
            "environment": "development"
        }
    }

    settings_path = temp_config_dir / "settings.yaml"
    with open(settings_path, "w", encoding='utf-8') as f:
        yaml.dump(settings, f, allow_unicode=True)

    return temp_config_dir
