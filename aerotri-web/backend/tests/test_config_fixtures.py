"""
Test configuration fixtures

验证配置测试 fixture 是否正常工作。
"""
import pytest
import yaml
from pathlib import Path


class TestConfigFixtures:
    """测试配置 fixtures"""

    def test_temp_config_dir(self, temp_config_dir):
        """测试临时配置目录 fixture"""
        assert temp_config_dir.exists()
        assert temp_config_dir.is_dir()

        # 创建一个测试文件
        test_file = temp_config_dir / "test.txt"
        test_file.write_text("test content")

        # 文件应该存在
        assert test_file.exists()

    def test_mock_defaults_yaml(self, mock_defaults_yaml):
        """测试 defaults.yaml fixture"""
        assert mock_defaults_yaml.exists()
        assert mock_defaults_yaml.name == "defaults.yaml"

        # 读取并验证内容
        with open(mock_defaults_yaml, 'r') as f:
            config = yaml.safe_load(f)

        assert "app" in config
        assert config["app"]["name"] == "AeroTri-Web"
        assert "paths" in config
        assert "algorithms" in config
        assert "colmap" in config["algorithms"]

    def test_mock_settings_yaml(self, mock_settings_yaml):
        """测试 settings.yaml fixture"""
        assert mock_settings_yaml.exists()
        assert mock_settings_yaml.name == "settings.yaml"

        # 读取并验证内容
        with open(mock_settings_yaml, 'r') as f:
            config = yaml.safe_load(f)

        assert "app" in config
        assert config["app"]["debug"] is True
        assert config["app"]["environment"] == "testing"

    def test_mock_project_root(self, mock_project_root):
        """测试项目根目录 fixture"""
        assert mock_project_root.exists()
        assert mock_project_root.is_dir()

        # 验证标准目录结构
        assert (mock_project_root / "data").exists()
        assert (mock_project_root / "data" / "outputs").exists()
        assert (mock_project_root / "backend").exists()

    def test_full_config_dir(self, full_config_dir):
        """测试完整配置目录 fixture"""
        assert full_config_dir.exists()

        # 应该包含 defaults.yaml 和 settings.yaml
        defaults_path = full_config_dir / "defaults.yaml"
        settings_path = full_config_dir / "settings.yaml"

        assert defaults_path.exists()
        assert settings_path.exists()

        # 读取并验证 defaults.yaml
        with open(defaults_path, 'r') as f:
            defaults = yaml.safe_load(f)

        assert "app" in defaults
        assert "paths" in defaults
        assert "database" in defaults
        assert "algorithms" in defaults
        assert "gaussian_splatting" in defaults
        assert "queue" in defaults

        # 验证 defaults.yaml 包含所有预期字段
        assert defaults["app"]["name"] == "AeroTri-Web"
        assert "colmap" in defaults["algorithms"]
        assert "glomap" in defaults["algorithms"]
        assert "instantsfm" in defaults["algorithms"]

        # 读取并验证 settings.yaml
        with open(settings_path, 'r') as f:
            settings = yaml.safe_load(f)

        assert settings["app"]["environment"] == "development"
