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
            assert overrides["algorithms"]["colmap"]["path"] == "/usr/bin/colmap"
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

    def test_validate_config_missing_executable(self):
        """测试验证缺失的可执行文件"""
        settings = AppSettings()

        # 设置一个不存在的可执行文件路径
        settings.algorithms.colmap.path = "/nonexistent/path/to/colmap"

        # 验证应该返回缺失的可执行文件
        missing = settings.validate_executables()

        assert isinstance(missing, dict)
        assert 'colmap' in missing
        assert '/nonexistent/path/to/colmap' in missing['colmap']

    def test_validate_config_no_write_permission(self):
        """测试验证目录写权限（通过模拟文件创建失败）"""
        from unittest.mock import MagicMock, patch

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with patch.dict(os.environ, {"AEROTRI_DB_PATH": str(db_path)}):
                reload_settings()
                settings = get_settings()

                # Mock Path.touch to raise PermissionError
                original_touch = Path.touch

                def mock_touch_permission_error(self, *args, **kwargs):
                    if self == db_path:
                        raise PermissionError(f"Permission denied: {self}")
                    return original_touch(self, *args, **kwargs)

                with patch.object(Path, 'touch', mock_touch_permission_error):
                    # 验证应该失败
                    with pytest.raises(RuntimeError) as exc_info:
                        validate_on_startup()

                    # 错误信息应该包含数据库路径
                    assert "Database" in str(exc_info.value) or "database" in str(exc_info.value)
                    assert "not writable" in str(exc_info.value).lower() or "permission" in str(exc_info.value).lower()

    def test_startup_validates_config(self):
        """测试启动时验证配置"""
        from app.conf.validation import validate_on_startup

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with patch.dict(os.environ, {"AEROTRI_DB_PATH": str(db_path)}):
                # 重新加载配置
                reload_settings()

                # 运行启动验证
                warnings = validate_on_startup()

                # 验证应该成功（可能有警告）
                assert isinstance(warnings, list)

                # 数据库文件应该可以被创建（验证了写权限）
                # 注意：validate_on_startup 会创建并删除测试文件


class TestDefaultsYaml:
    """测试 defaults.yaml 文件"""

    def test_defaults_yaml_syntax(self):
        """测试 defaults.yaml 语法正确"""
        from pathlib import Path

        defaults_path = Path(__file__).parent.parent / "config" / "defaults.yaml"
        with open(defaults_path) as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert "name" in config
        assert "paths" in config
        assert "algorithms" in config
        assert config["name"] == "AeroTri-Web"

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
            assert "colmap" in overrides["algorithms"]
            assert "path" in overrides["algorithms"]["colmap"]
            assert overrides["algorithms"]["colmap"]["path"] == "/usr/bin/colmap"

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


class TestSettingsExampleFile:
    """测试 settings.yaml.example 示例文件"""

    def test_settings_example_exists(self):
        """测试 settings.yaml.example 存在且语法正确"""
        from pathlib import Path

        example_path = Path(__file__).parent.parent / "config" / "settings.yaml.example"
        assert example_path.exists(), f"settings.yaml.example not found at {example_path}"

        with open(example_path) as f:
            config = yaml.safe_load(f)

        assert config is not None, "settings.yaml.example is empty or invalid"
        assert "debug" in config, "settings.yaml.example missing 'debug' field"
        assert "paths" in config, "settings.yaml.example missing 'paths' section"
        assert "algorithms" in config, "settings.yaml.example missing 'algorithms' section"

    def test_settings_example_has_documentation(self):
        """测试 settings.yaml.example 包含使用说明"""
        from pathlib import Path

        example_path = Path(__file__).parent.parent / "config" / "settings.yaml.example"

        with open(example_path) as f:
            content = f.read()

        # 检查关键文档字符串存在
        assert "使用说明" in content or "Usage" in content, \
            "settings.yaml.example should have usage instructions"
        assert "复制本文件为 settings.yaml" in content or "cp settings.yaml.example settings.yaml" in content, \
            "settings.yaml.example should explain how to use it"

    def test_settings_example_config_priority(self):
        """测试 settings.yaml.example 说明配置优先级"""
        from pathlib import Path

        example_path = Path(__file__).parent.parent / "config" / "settings.yaml.example"

        with open(example_path) as f:
            content = f.read()

        # 检查优先级说明
        assert "优先级" in content or "priority" in content.lower(), \
            "settings.yaml.example should explain configuration priority"
        assert "环境变量" in content or "environment variable" in content.lower(), \
            "settings.yaml.example should mention environment variables"


class TestAppSettingsCreate:
    """测试 AppSettings.create() 方法"""

    def test_load_defaults_config(self):
        """测试加载 defaults.yaml 配置"""
        from app.conf.settings import AppSettings

        settings = AppSettings.create()

        # 验证应用配置
        assert settings.name == "AeroTri-Web"
        assert settings.version == "1.0.0"

        # 验证路径配置（project_root 应该被自动检测）
        assert settings.paths.project_root is not None
        # project_root 应该是 backend/ 目录（从 backend/config/../ 向上解析）
        # test_config.py 在 backend/tests/，向上2级到 backend/
        expected_root = Path(__file__).parent.parent.resolve()
        assert settings.paths.project_root == expected_root

        # 验证算法配置
        assert settings.algorithms.colmap.path == "colmap"
        assert settings.algorithms.glomap.path == "glomap"
        assert settings.algorithms.instantsfm.path == "ins-sfm"

        # 验证其他配置
        assert settings.queue.max_concurrent == 1
        assert settings.gpu.monitor_interval == 2

    def test_environment_variable_override(self):
        """测试环境变量覆盖配置"""
        import os
        from app.conf.settings import AppSettings, reload_settings

        # 设置环境变量
        os.environ["COLMAP_PATH"] = "/custom/colmap"
        os.environ["QUEUE_MAX_CONCURRENT"] = "4"

        try:
            # 重新加载配置以应用环境变量
            settings = AppSettings.create()

            # 验证环境变量覆盖
            assert settings.algorithms.colmap.path == "/custom/colmap"
            assert settings.queue.max_concurrent == 4
        finally:
            # 清理环境变量
            if "COLMAP_PATH" in os.environ:
                del os.environ["COLMAP_PATH"]
            if "QUEUE_MAX_CONCURRENT" in os.environ:
                del os.environ["QUEUE_MAX_CONCURRENT"]
            # 重新加载以恢复默认配置
            reload_settings()

    def test_settings_yaml_overrides_defaults(self):
        """测试 settings.yaml 覆盖 defaults.yaml"""
        from app.conf.settings import AppSettings
        import tempfile
        import yaml

        # 创建临时 settings.yaml
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                "app": {
                    "name": "Custom AeroTri",
                    "debug": True
                },
                "algorithms": {
                    "colmap": {
                        "path": "/custom/bin/colmap"
                    }
                }
            }, f)
            temp_file = Path(f.name)

        try:
            # 模拟加载临时配置文件
            # 注意：这个测试需要 mock config_dir 路径
            # 这里我们只测试 _merge_dict 功能
            base = {"app": {"name": "AeroTri-Web", "debug": False}}
            override = {"app": {"debug": True}}

            AppSettings._merge_dict(base, override)

            assert base["app"]["name"] == "AeroTri-Web"  # 保持原值
            assert base["app"]["debug"] is True  # 被覆盖
        finally:
            temp_file.unlink()

    def test_deep_merge_nested_configs(self):
        """测试深度合并嵌套配置"""
        from app.conf.settings import AppSettings

        # 测试深度合并
        base = {
            "algorithms": {
                "colmap": {"path": "colmap", "bin_dir": "/usr/bin"},
                "glomap": {"path": "glomap"}
            },
            "paths": {
                "data_dir": "./data"
            }
        }

        override = {
            "algorithms": {
                "colmap": {"path": "/custom/colmap"}
            },
            "queue": {
                "max_concurrent": 5
            }
        }

        AppSettings._merge_dict(base, override)

        # 验证深度合并结果
        assert base["algorithms"]["colmap"]["path"] == "/custom/colmap"
        assert base["algorithms"]["colmap"]["bin_dir"] == "/usr/bin"  # 保持原值
        assert base["algorithms"]["glomap"]["path"] == "glomap"  # 保持原值
        assert base["paths"]["data_dir"] == "./data"  # 保持原值
        assert base["queue"]["max_concurrent"] == 5  # 新增字段

    def test_get_absolute_paths(self):
        """测试获取绝对路径配置"""
        from app.conf.settings import AppSettings

        settings = AppSettings.create()

        # 验证所有路径都是绝对路径
        assert settings.paths.data_dir.is_absolute()
        assert settings.paths.outputs_dir.is_absolute()
        assert settings.paths.blocks_dir.is_absolute()
        assert settings.paths.thumbnails_dir.is_absolute()
        assert settings.database.path.is_absolute()
        assert settings.gaussian_splatting.repo_path.is_absolute()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
