"""
Test fixtures package

这个包包含可重用的测试 fixtures。
虽然 conftest.py 中的 fixtures 会被 pytest 自动发现，
但将 fixtures 组织在单独的文件中可以提高代码可维护性。
"""
from .config_fixtures import *  # noqa: F401, F403

__all__ = [
    'temp_config_dir',
    'mock_defaults_yaml',
    'mock_settings_yaml',
    'mock_project_root',
    'full_config_dir',
]
