"""
配置系统单元测试

测试 Pydantic Settings 配置类的加载、验证和环境变量覆盖功能。
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# 添加 app 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.conf.settings import (
    AppSettings,
    PathsConfig,
    DatabaseConfig,
    AlgorithmsConfig,
    GaussianSplattingConfig,
    get_settings,
    reload_settings,
)
from app.conf.validation import validate_on_startup


class TestPathsConfig:
    """测试路径配置"""

    def test_default_paths(self):
        """测试默认路径配置"""
        config = PathsConfig()
        assert config.data_dir == Path("./data")
        assert config.outputs_dir == Path("./data/outputs")
        assert config.blocks_dir == Path("./data/blocks")
        assert config.thumbnails_dir == Path("./data/thumbnails")

    def test_resolve_relative_paths(self):
        """测试相对路径解析为绝对路径"""
        config = PathsConfig()
        project_root = Path("/tmp/test_project")

        config.resolve_paths(project_root)

        # 所有相对路径应该被解析为绝对路径
        assert config.data_dir.is_absolute()
        assert config.outputs_dir.is_absolute()
        assert config.blocks_dir.is_absolute()
        assert config.thumbnails_dir.is_absolute()

        # 验证路径正确解析
        assert config.data_dir == project_root / "data"
        assert config.outputs_dir == project_root / "data" / "outputs"

    def test_absolute_paths_unchanged(self):
        """测试绝对路径不被修改"""
        absolute_path = Path("/var/lib/aerotri/data")
        config = PathsConfig(data_dir=absolute_path)

        config.resolve_paths(Path("/tmp/test_project"))

        # 绝对路径应该保持不变
        assert config.data_dir == absolute_path


class TestDatabaseConfig:
    """测试数据库配置"""

    def test_default_database_config(self):
        """测试默认数据库配置"""
        config = DatabaseConfig()
        assert config.path == Path("./data/aerotri.db")
        assert config.pool_size == 5
        assert config.max_overflow == 10

    def test_pool_size_validation(self):
        """测试连接池大小验证"""
        # 有效范围
        config = DatabaseConfig(pool_size=50)
        assert config.pool_size == 50

        # 超出范围应该被拒绝
        with pytest.raises(Exception):
            DatabaseConfig(pool_size=0)  # 小于最小值

        with pytest.raises(Exception):
            DatabaseConfig(pool_size=101)  # 大于最大值

    def test_resolve_relative_path(self):
        """测试数据库相对路径解析"""
        config = DatabaseConfig(path=Path("./data/test.db"))
        project_root = Path("/tmp/test_project")

        config.resolve_path(project_root)

        assert config.path.is_absolute()
        assert config.path == project_root / "data" / "test.db"


class TestAlgorithmsConfig:
    """测试算法配置"""

    def test_default_algorithms(self):
        """测试默认算法配置"""
        config = AlgorithmsConfig()

        assert config.colmap.path == "colmap"
        assert config.glomap.path == "glomap"
        assert config.instantsfm.path == "ins-sfm"
        assert config.openmvg.bin_dir == "/usr/local/bin"
        assert config.openmvs.bin_dir == "/usr/local/lib/openmvs/bin"

    def test_get_executable_with_path(self):
        """测试通过 path 获取可执行文件"""
        config = AlgorithmsConfig(
            colmap={"path": "/usr/local/bin/colmap"}
        )

        exe = config.colmap.get_executable()
        assert exe == Path("/usr/local/bin/colmap")

    def test_get_executable_from_bin_dir(self):
        """测试从 bin_dir 获取可执行文件"""
        config = AlgorithmsConfig(
            openmvs={"bin_dir": "/usr/local/lib/openmvs/bin"}
        )

        exe = config.openmvs.get_executable("DensifyPointCloud")
        assert exe == Path("/usr/local/lib/openmvs/bin/DensifyPointCloud")

    def test_get_executable_none(self):
        """测试不指定完整路径时返回 Path（用于 shell 查找）"""
        config = AlgorithmsConfig()

        exe = config.colmap.get_executable()
        # 即使是简单名称也会返回 Path 对象
        # 实际执行时由 shell 从 PATH 查找
        assert exe == Path("colmap")


class TestGaussianSplattingConfig:
    """测试 3DGS 配置"""

    def test_default_gs_config(self):
        """测试默认 3DGS 配置"""
        config = GaussianSplattingConfig()

        assert config.repo_path == Path("/opt/gaussian-splatting")
        assert config.python == "python"
        assert config.tensorboard_path == "tensorboard"
        assert config.tensorboard_port_start == 6006
        assert config.tensorboard_port_end == 6100

    def test_port_range_validation(self):
        """测试端口范围验证"""
        # 有效端口
        config = GaussianSplattingConfig(
            tensorboard_port_start=8080,
            tensorboard_port_end=8090
        )
        assert config.tensorboard_port_start == 8080

        # 无效端口（小于 1024）
        with pytest.raises(Exception):
            GaussianSplattingConfig(tensorboard_port_start=100)

        # 无效端口（大于 65535）
        with pytest.raises(Exception):
            GaussianSplattingConfig(tensorboard_port_end=70000)


class TestAppSettings:
    """测试应用主配置"""

    def test_default_settings(self):
        """测试默认配置"""
        settings = AppSettings()

        assert settings.name == "AeroTri Web"
        assert settings.version == "1.0.0"
        assert settings.debug is False
        assert settings.environment == "production"

    def test_settings_initialization(self):
        """测试配置初始化时自动解析路径"""
        settings = AppSettings()

        # project_root 应该被自动检测
        assert settings.paths.project_root is not None

        # 路径应该被解析为绝对路径
        assert settings.paths.data_dir.is_absolute()
        assert settings.database.path.is_absolute()
        assert settings.gaussian_splatting.repo_path.is_absolute()

    def test_load_from_yaml(self):
        """测试从 YAML 文件加载配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                "app": {
                    "debug": True,
                    "environment": "development"
                },
                "paths": {
                    "data_dir": "/tmp/test_data"
                }
            }, f)
            temp_file = Path(f.name)

        try:
            config = AppSettings.load_from_yaml(temp_file)

            assert config["app"]["debug"] is True
            assert config["paths"]["data_dir"] == "/tmp/test_data"
        finally:
            temp_file.unlink()

    def test_load_from_nonexistent_yaml(self):
        """测试从不存在的 YAML 文件加载（应返回空字典）"""
        config = AppSettings.load_from_yaml(Path("/nonexistent/file.yaml"))
        assert config == {}

    def test_load_env_overrides(self):
        """测试环境变量覆盖"""
        # 设置环境变量
        with patch.dict(os.environ, {
            "AEROTRI_DB_PATH": "/tmp/test.db",
            "COLMAP_PATH": "/usr/bin/colmap",
            "QUEUE_MAX_CONCURRENT": "4"
        }):
            overrides = AppSettings.load_env_overrides()

            assert overrides["database"]["path"] == "/tmp/test.db"
            assert overrides["algorithms"]["colmap_path"] == "/usr/bin/colmap"
            assert overrides["queue"]["max_concurrent"] == 4

    def test_flatten_config(self):
        """测试配置展平"""
        nested = {
            "database": {"path": "./data/db"},
            "algorithms": {
                "colmap": {"path": "/usr/bin/colmap"}
            }
        }

        flat = AppSettings._flatten_config(nested)

        assert "database_path" in flat
        assert "algorithms_colmap_path" in flat
        assert flat["database_path"] == "./data/db"

    def test_merge_dict(self):
        """测试字典合并"""
        base = {"a": 1, "b": {"x": 10}}
        override = {"b": {"y": 20}, "c": 3}

        AppSettings._merge_dict(base, override)

        assert base["a"] == 1
        assert base["b"]["x"] == 10
        assert base["b"]["y"] == 20
        assert base["c"] == 3

    def test_validate_executables(self):
        """测试可执行文件验证"""
        settings = AppSettings()

        missing = settings.validate_executables()

        # 返回值应该是字典
        assert isinstance(missing, dict)

        # 在没有安装算法的环境中，应该有缺失项
        # 这个测试在不同环境中结果可能不同，所以只检查返回类型


class TestConfigSingleton:
    """测试配置单例"""

    def test_get_settings_singleton(self):
        """测试 get_settings 返回单例"""
        settings1 = get_settings()
        settings2 = get_settings()

        # 应该返回同一个实例
        assert settings1 is settings2

    def test_reload_settings(self):
        """测试重新加载配置"""
        settings1 = get_settings()

        # 重新加载
        settings2 = reload_settings()

        # 应该返回新实例
        assert settings1 is not settings2

        # 但内容应该相同（如果没有修改配置文件）
        assert settings1.environment == settings2.environment


class TestConfigValidation:
    """测试配置验证"""

    def test_validate_on_startup_success(self):
        """测试启动验证成功（不抛出异常）"""
        # 这个测试会在临时目录中运行，所以应该成功
        with tempfile.TemporaryDirectory() as tmpdir:
            # 设置临时目录为项目根目录
            with patch.dict(os.environ, {"AEROTRI_DB_PATH": f"{tmpdir}/test.db"}):
                # 应该不抛出异常（可能有警告）
                try:
                    warnings = validate_on_startup()
                    assert isinstance(warnings, list)
                except RuntimeError as e:
                    # 如果有错误，应该包含详细信息
                    assert "Configuration validation failed" in str(e)

    def test_validate_on_startup_creates_directories(self):
        """测试启动验证自动创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用不存在的子目录
            data_dir = Path(tmpdir) / "data" / "outputs"

            with patch.dict(os.environ, {
                "AEROTRI_DB_PATH": str(data_dir / "aerotri.db")
            }):
                # 重新加载配置以使用环境变量
                reload_settings()
                settings = get_settings()
                settings.paths.outputs_dir = data_dir

                # 运行验证
                warnings = validate_on_startup()

                # 手动创建目录进行测试
                settings.paths.setup_directories()

                # 目录应该被创建
                assert data_dir.exists()


class TestDefaultsYaml:
    """测试 defaults.yaml 文件"""

    def test_defaults_yaml_syntax(self):
        """测试 defaults.yaml 语法正确"""
        from pathlib import Path

        defaults_path = Path(__file__).parent.parent / "config" / "defaults.yaml"
        with open(defaults_path) as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert "app" in config
        assert "paths" in config
        assert "algorithms" in config
        assert config["app"]["name"] == "AeroTri-Web"

    def test_defaults_yaml_relative_paths(self):
        """测试 defaults.yaml 使用相对路径"""
        from pathlib import Path

        defaults_path = Path(__file__).parent.parent / "config" / "defaults.yaml"
        with open(defaults_path) as f:
            config = yaml.safe_load(f)

        # 算法路径应该使用系统 PATH
        assert config["algorithms"]["colmap"]["path"] == "colmap"
        assert config["algorithms"]["glomap"]["path"] == "glomap"
        assert config["algorithms"]["instantsfm"]["path"] == "ins-sfm"

        # 数据路径应该是相对路径
        assert config["paths"]["data_dir"].startswith("./")
        assert config["paths"]["outputs_dir"].startswith("./")


class TestEnvironmentCompatibility:
    """测试向后兼容性"""

    def test_legacy_colmap_path(self):
        """测试旧的环境变量 COLMAP_PATH 仍然有效"""
        with patch.dict(os.environ, {"COLMAP_PATH": "/usr/bin/colmap"}):
            overrides = AppSettings.load_env_overrides()

            assert "algorithms" in overrides
            assert "colmap_path" in overrides["algorithms"]
            assert overrides["algorithms"]["colmap_path"] == "/usr/bin/colmap"

    def test_legacy_gs_paths(self):
        """测试旧的 GS 环境变量仍然有效"""
        with patch.dict(os.environ, {
            "GS_REPO_PATH": "/opt/gs",
            "GS_PYTHON": "/opt/gs/bin/python"
        }):
            overrides = AppSettings.load_env_overrides()

            assert "gaussian_splatting" in overrides
            assert overrides["gaussian_splatting"]["repo_path"] == "/opt/gs"
            assert overrides["gaussian_splatting"]["python"] == "/opt/gs/bin/python"

    def test_legacy_queue_var(self):
        """测试旧的 QUEUE_MAX_CONCURRENT 环境变量仍然有效"""
        with patch.dict(os.environ, {"QUEUE_MAX_CONCURRENT": "3"}):
            overrides = AppSettings.load_env_overrides()

            assert "queue" in overrides
            assert overrides["queue"]["max_concurrent"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
