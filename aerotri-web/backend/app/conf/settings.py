"""
统一的配置管理系统
使用 Pydantic Settings 实现类型安全的配置

配置优先级 (高到低):
1. 环境变量
2. settings.{environment}.yaml (如 settings.development.yaml)
3. settings.yaml
4. defaults.yaml
"""
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# 路径配置
# ============================================================================

class PathsConfig(BaseModel):
    """路径配置

    支持相对路径和绝对路径。相对路径会自动解析为相对于 project_root 的绝对路径。
    """
    data_dir: Path = Field(default=Path("./data"), description="数据目录")
    outputs_dir: Path = Field(default=Path("./data/outputs"), description="任务输出目录")
    blocks_dir: Path = Field(default=Path("./data/blocks"), description="Block工作目录")
    thumbnails_dir: Path = Field(default=Path("./data/thumbnails"), description="缩略图缓存")
    project_root: Optional[Path] = Field(default=None, description="项目根目录（自动检测）")

    def resolve_paths(self, project_root: Path) -> None:
        """解析相对路径为绝对路径

        Args:
            project_root: 项目根目录，用于解析相对路径
        """
        if self.project_root is None:
            self.project_root = project_root

        # 解析相对路径
        for attr in ['data_dir', 'outputs_dir', 'blocks_dir', 'thumbnails_dir']:
            value = getattr(self, attr)
            if not isinstance(value, Path):
                value = Path(value)
            if not value.is_absolute():
                # 相对于 project_root
                value = project_root / value
            object.__setattr__(self, attr, value.resolve())

    def setup_directories(self) -> None:
        """创建必要的目录"""
        for attr in ['data_dir', 'outputs_dir', 'blocks_dir', 'thumbnails_dir']:
            path = getattr(self, attr)
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {path}")
            except Exception as e:
                logger.error(f"Failed to create directory {path}: {e}")
                raise


# ============================================================================
# 数据库配置
# ============================================================================

class DatabaseConfig(BaseModel):
    """数据库配置"""
    path: Path = Field(default=Path("./data/aerotri.db"), description="数据库路径")
    pool_size: int = Field(default=5, ge=1, le=100, description="连接池大小")
    max_overflow: int = Field(default=10, ge=0, le=100, description="最大溢出连接数")

    def resolve_path(self, project_root: Path) -> None:
        """解析数据库路径（如果为相对路径）"""
        if not isinstance(self.path, Path):
            self.path = Path(self.path)
        if not self.path.is_absolute():
            self.path = (project_root / self.path).resolve()


# ============================================================================
# 算法配置
# ============================================================================

class AlgorithmConfig(BaseModel):
    """单个算法配置"""
    path: Optional[str] = Field(default=None, description="可执行文件路径（直接使用）")
    bin_dir: Optional[str] = Field(default=None, description="二进制文件目录")
    sensor_db: Optional[str] = Field(default=None, description="传感器数据库路径（OpenMVG）")

    def get_executable(self, exe_name: Optional[str] = None) -> Optional[Path]:
        """获取可执行文件路径

        Args:
            exe_name: 可执行文件名（如 "colmap"），如果 path 已设置则忽略

        Returns:
            可执行文件的绝对路径，如果配置为从 PATH 查找则返回 None
        """
        if self.path:
            return Path(self.path)
        if self.bin_dir and exe_name:
            return Path(self.bin_dir) / exe_name
        # 假设在 PATH 中查找
        return None


class AlgorithmsConfig(BaseModel):
    """算法配置集合"""
    colmap: AlgorithmConfig = Field(
        default_factory=lambda: AlgorithmConfig(path="colmap"),
        description="COLMAP 配置"
    )
    glomap: AlgorithmConfig = Field(
        default_factory=lambda: AlgorithmConfig(path="glomap"),
        description="GLOMAP 配置"
    )
    instantsfm: AlgorithmConfig = Field(
        default_factory=lambda: AlgorithmConfig(path="ins-sfm"),
        description="InstantSfM 配置"
    )
    openmvg: AlgorithmConfig = Field(
        default_factory=lambda: AlgorithmConfig(
            bin_dir="/usr/local/bin",
            sensor_db="/usr/local/share/sensor_width_camera_database.txt"
        ),
        description="OpenMVG 配置"
    )
    openmvs: AlgorithmConfig = Field(
        default_factory=lambda: AlgorithmConfig(
            bin_dir="/usr/local/lib/openmvs/bin"
        ),
        description="OpenMVS 配置"
    )


# ============================================================================
# 3D Gaussian Splatting 配置
# ============================================================================

class GaussianSplattingConfig(BaseModel):
    """3D Gaussian Splatting 配置"""
    repo_path: Path = Field(
        default=Path("/opt/gaussian-splatting"),
        description="3DGS 仓库路径（包含 train.py）"
    )
    python: str = Field(default="python", description="Python 解释器路径")
    tensorboard_path: str = Field(default="tensorboard", description="TensorBoard 可执行文件")
    tensorboard_port_start: int = Field(default=6006, ge=1024, le=65535)
    tensorboard_port_end: int = Field(default=6100, ge=1024, le=65535)
    network_gui_ip: str = Field(default="127.0.0.1")
    network_gui_port_start: int = Field(default=6009, ge=1024, le=65535)
    network_gui_port_end: int = Field(default=6109, ge=1024, le=65535)

    def resolve_repo_path(self, project_root: Path) -> None:
        """解析仓库路径（如果为相对路径）"""
        if not isinstance(self.repo_path, Path):
            self.repo_path = Path(self.repo_path)
        if not self.repo_path.is_absolute():
            self.repo_path = (project_root / self.repo_path).resolve()


# ============================================================================
# SPZ 压缩配置
# ============================================================================

class SpzConfig(BaseModel):
    """SPZ 压缩配置"""
    python: str = Field(default="python", description="包含 SPZ Python 绑定的解释器")


# ============================================================================
# 队列配置
# ============================================================================

class QueueConfig(BaseModel):
    """队列配置"""
    max_concurrent: int = Field(default=1, ge=1, le=10, description="最大并发任务数")
    scheduler_interval: int = Field(default=5, ge=1, le=60, description="调度间隔（秒）")


# ============================================================================
# GPU 配置
# ============================================================================

class GPUConfig(BaseModel):
    """GPU 配置"""
    monitor_interval: int = Field(default=2, ge=1, description="监控间隔（秒）")
    auto_selection: str = Field(
        default="most_free",
        description="自动选择策略: most_free | least_used | first_available"
    )
    default_device: int = Field(default=0, ge=0, description="默认 GPU 设备索引")

    @field_validator("auto_selection")
    @classmethod
    def validate_auto_selection(cls, v: str) -> str:
        valid_values = ["most_free", "least_used", "first_available"]
        if v not in valid_values:
            logger.warning(f"Invalid auto_selection '{v}', using 'most_free'")
            return "most_free"
        return v


# ============================================================================
# 通知服务配置
# ============================================================================

class DingTalkChannelConfig(BaseModel):
    """钉钉通知通道配置"""
    enabled: bool = False
    webhook_url: str = ""
    secret: str = ""
    events: List[str] = Field(default_factory=list)


class DingTalkConfig(BaseModel):
    """钉钉通知配置"""
    channels: Dict[str, DingTalkChannelConfig] = Field(default_factory=dict)


class FeishuConfig(BaseModel):
    """飞书通知配置"""
    enabled: bool = False
    channels: Dict[str, Any] = Field(default_factory=dict)


class PeriodicNotificationConfig(BaseModel):
    """周期性通知配置"""
    task_summary: Dict[str, Any] = Field(default_factory=lambda: {"enabled": False, "cron": "0 21 * * *"})
    system_status: Dict[str, Any] = Field(default_factory=lambda: {"enabled": False, "interval": 14400})


class NotificationConfig(BaseModel):
    """通知服务配置"""
    enabled: bool = Field(default=False, description="是否启用通知服务")
    dingtalk: DingTalkConfig = Field(default_factory=DingTalkConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    periodic: PeriodicNotificationConfig = Field(default_factory=PeriodicNotificationConfig)


# ============================================================================
# 监控配置
# ============================================================================

class MonitoringGPUMonitor(BaseModel):
    """GPU 监控配置"""
    interval_seconds: int = Field(default=2, ge=1, description="监控间隔（秒）")


class MonitoringQueueMonitor(BaseModel):
    """队列监控配置"""
    interval_seconds: int = Field(default=10, ge=1, description="监控间隔（秒）")


class MonitoringSystemMonitor(BaseModel):
    """系统监控配置"""
    interval_seconds: int = Field(default=60, ge=1, description="监控间隔（秒）")


class MonitoringConfig(BaseModel):
    """监控配置"""
    gpu: MonitoringGPUMonitor = Field(default_factory=MonitoringGPUMonitor)
    queue: MonitoringQueueMonitor = Field(default_factory=MonitoringQueueMonitor)
    system: MonitoringSystemMonitor = Field(default_factory=MonitoringSystemMonitor)


# ============================================================================
# 诊断Agent配置
# ============================================================================

class DiagnosticConfig(BaseModel):
    """诊断Agent配置模型

    可选功能：任务失败时自动调用OpenClaw进行AI诊断。
    默认禁用，适合开源环境。
    """
    enabled: bool = Field(
        default=False,
        description="是否启用诊断Agent（默认关闭）"
    )
    openclaw_cmd: str = Field(
        default="openclaw",
        description="OpenClaw CLI命令路径"
    )
    agent_id: str = Field(
        default="main",
        description="OpenClaw Agent ID"
    )
    agent_memory_path: Path = Field(
        default=Path("./data/diagnostics/AerotriWeb_AGENT.md"),
        description="Agent知识库路径"
    )
    history_log_path: Path = Field(
        default=Path("./data/diagnostics/diagnosis_history.log"),
        description="诊断历史日志路径"
    )
    claude_md_path: Path = Field(
        default=Path("./CLAUDE.md"),
        description="项目文档路径（CLAUDE.md）"
    )
    context_output_dir: Path = Field(
        default=Path("./data/diagnostics/contexts"),
        description="上下文持久化目录（存储发送给OpenClaw的完整上下文，用于调试）"
    )
    timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=600,
        description="OpenClaw调用超时时间（秒）"
    )
    auto_fix: bool = Field(
        default=False,
        description="是否尝试自动修复（谨慎启用）"
    )

    def resolve_paths(self, project_root: Path) -> None:
        """解析相对路径为绝对路径

        支持绝对路径和相对路径：
        - 绝对路径：直接使用，不修改
        - 相对路径：相对于 project_root 解析

        Args:
            project_root: 项目根目录
        """
        for attr in ['agent_memory_path', 'history_log_path', 'claude_md_path', 'context_output_dir']:
            value = getattr(self, attr)
            if not isinstance(value, Path):
                value = Path(value)
            # 如果是绝对路径，直接使用
            if value.is_absolute():
                logger.debug(f"Diagnostic {attr}: using absolute path {value}")
            # 如果是相对路径，相对于 project_root 解析
            else:
                value = (project_root / value).resolve()
                logger.debug(f"Diagnostic {attr}: resolved to {value}")
            object.__setattr__(self, attr, value)

    def setup_directories(self) -> None:
        """创建必要的目录"""
        # 创建诊断数据目录
        diag_dir = self.agent_memory_path.parent
        try:
            diag_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured diagnostics directory exists: {diag_dir}")
        except Exception as e:
            logger.warning(f"Failed to create diagnostics directory {diag_dir}: {e}")

        # 创建上下文输出目录
        context_dir = self.context_output_dir
        try:
            context_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured context output directory exists: {context_dir}")
        except Exception as e:
            logger.warning(f"Failed to create context output directory {context_dir}: {e}")


# ============================================================================
# 图像根路径配置
# ============================================================================

class ImageRootModel(BaseModel):
    """图像根路径配置模型（用于新配置系统）"""
    default: str = Field(default="./data/images", description="默认图像路径")
    paths: List[Dict[str, str]] = Field(
        default_factory=list,
        description="命名路径列表 [{name: str, path: str}]"
    )


# ============================================================================
# 应用主配置
# ============================================================================

class AppSettings(BaseModel):
    """
    应用主配置类

    配置优先级 (高到低):
    1. 环境变量
    2. settings.{environment}.yaml
    3. settings.yaml
    4. defaults.yaml
    """
    # 应用配置
    name: str = Field(default="AeroTri Web", description="应用名称")
    version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    environment: str = Field(default="production", description="运行环境")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="允许的 CORS 源"
    )

    # 日志
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: Optional[str] = Field(default=None, description="日志文件路径")

    # 子配置
    paths: PathsConfig = Field(default_factory=PathsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    algorithms: AlgorithmsConfig = Field(default_factory=AlgorithmsConfig)
    gaussian_splatting: GaussianSplattingConfig = Field(
        default_factory=GaussianSplattingConfig
    )
    spz: SpzConfig = Field(default_factory=SpzConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    gpu: GPUConfig = Field(default_factory=GPUConfig)
    image_roots: ImageRootModel = Field(default_factory=ImageRootModel)
    diagnostic: DiagnosticConfig = Field(default_factory=DiagnosticConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    def __init__(self, **data):
        """初始化配置并解析路径"""
        super().__init__(**data)

        # 自动检测项目根目录
        if self.paths.project_root is None:
            # backend/app/conf/settings.py -> backend/ (向上 3 级)
            config_dir = Path(__file__).resolve()
            project_root = config_dir.parent.parent.parent
            self.paths.resolve_paths(project_root)

        # 解析数据库路径
        self.database.resolve_path(self.paths.project_root)

        # 解析 3DGS 仓库路径
        self.gaussian_splatting.resolve_repo_path(self.paths.project_root)

        # 解析诊断Agent路径
        self.diagnostic.resolve_paths(self.paths.project_root)

    @classmethod
    def load_from_yaml(cls, config_file: Path) -> Dict[str, Any]:
        """从 YAML 文件加载配置

        Args:
            config_file: YAML 配置文件路径

        Returns:
            配置字典，文件不存在返回空字典
        """
        if not config_file.exists():
            logger.debug(f"Config file not found: {config_file}")
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
                logger.info(f"Loaded config from: {config_file}")
                return config
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML {config_file}: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Failed to load config {config_file}: {e}")
            return {}

    @classmethod
    def load_env_overrides(cls) -> Dict[str, Any]:
        """加载环境变量覆盖

        支持以下环境变量（优先级高于 YAML）:
        - AEROTRI_DB_PATH
        - COLMAP_PATH, GLOMAP_PATH, INSTANTSFM_PATH
        - OPENMVG_BIN_DIR, OPENMVG_SENSOR_DB
        - OPENMVS_BIN_DIR
        - GS_REPO_PATH, GS_PYTHON
        - SPZ_PYTHON
        - TENSORBOARD_PATH
        - AEROTRI_IMAGE_ROOT, AEROTRI_IMAGE_ROOTS
        - QUEUE_MAX_CONCURRENT
        - AEROTRI_FRONTEND_ORIGIN
        - AEROTRI_CORS_ORIGINS

        Returns:
            环境变量覆盖字典
        """
        overrides: Dict[str, Any] = {}

        # 数据库路径
        if "AEROTRI_DB_PATH" in os.environ:
            overrides.setdefault("database", {})["path"] = os.getenv("AEROTRI_DB_PATH")

        # 算法路径
        if "COLMAP_PATH" in os.environ:
            overrides.setdefault("algorithms", {}).setdefault("colmap", {})["path"] = os.getenv("COLMAP_PATH")
        if "GLOMAP_PATH" in os.environ:
            overrides.setdefault("algorithms", {}).setdefault("glomap", {})["path"] = os.getenv("GLOMAP_PATH")
        if "INSTANTSFM_PATH" in os.environ:
            overrides.setdefault("algorithms", {}).setdefault("instantsfm", {})["path"] = os.getenv("INSTANTSFM_PATH")
        if "OPENMVG_BIN_DIR" in os.environ:
            overrides.setdefault("algorithms", {}).setdefault("openmvg", {})["bin_dir"] = os.getenv("OPENMVG_BIN_DIR")
        if "OPENMVG_SENSOR_DB" in os.environ:
            overrides.setdefault("algorithms", {}).setdefault("openmvg", {})["sensor_db"] = os.getenv("OPENMVG_SENSOR_DB")
        if "OPENMVS_BIN_DIR" in os.environ:
            overrides.setdefault("algorithms", {}).setdefault("openmvs", {})["bin_dir"] = os.getenv("OPENMVS_BIN_DIR")

        # 3DGS 配置
        if "GS_REPO_PATH" in os.environ:
            overrides.setdefault("gaussian_splatting", {})["repo_path"] = os.getenv("GS_REPO_PATH")
        if "GS_PYTHON" in os.environ:
            overrides.setdefault("gaussian_splatting", {})["python"] = os.getenv("GS_PYTHON")
        if "TENSORBOARD_PATH" in os.environ:
            overrides.setdefault("gaussian_splatting", {})["tensorboard_path"] = os.getenv("TENSORBOARD_PATH")
        if "SPZ_PYTHON" in os.environ:
            overrides.setdefault("spz", {})["python"] = os.getenv("SPZ_PYTHON")

        # 图像根路径
        if "AEROTRI_IMAGE_ROOT" in os.environ:
            overrides.setdefault("image_roots", {})["default"] = os.getenv("AEROTRI_IMAGE_ROOT")
        # AEROTRI_IMAGE_ROOTS 由 config.py 中的 get_image_roots() 处理

        # 队列配置
        if "QUEUE_MAX_CONCURRENT" in os.environ:
            overrides.setdefault("queue", {})["max_concurrent"] = int(os.getenv("QUEUE_MAX_CONCURRENT", "1"))

        # CORS
        if "AEROTRI_CORS_ORIGINS" in os.environ:
            origins_raw = os.getenv("AEROTRI_CORS_ORIGINS", "")
            origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
            if origins:
                overrides["cors_origins"] = origins
        elif "AEROTRI_FRONTEND_ORIGIN" in os.environ:
            origin = os.getenv("AEROTRI_FRONTEND_ORIGIN", "").strip()
            if origin:
                overrides["cors_origins"] = [origin]

        # 应用配置
        if "AEROTRI_DEBUG" in os.environ:
            overrides["debug"] = os.getenv("AEROTRI_DEBUG", "false").lower() == "true"
        if "AEROTRI_ENV" in os.environ:
            overrides["environment"] = os.getenv("AEROTRI_ENV", "production")

        # 诊断Agent配置
        if "AEROTRI_DIAGNOSTIC_ENABLED" in os.environ:
            overrides.setdefault("diagnostic", {})["enabled"] = (
                os.getenv("AEROTRI_DIAGNOSTIC_ENABLED", "false").lower() == "true"
            )
        if "AEROTRI_DIAGNOSTIC_OPENCLAW_CMD" in os.environ:
            overrides.setdefault("diagnostic", {})["openclaw_cmd"] = os.getenv("AEROTRI_DIAGNOSTIC_OPENCLAW_CMD")
        if "AEROTRI_DIAGNOSTIC_AUTO_FIX" in os.environ:
            overrides.setdefault("diagnostic", {})["auto_fix"] = (
                os.getenv("AEROTRI_DIAGNOSTIC_AUTO_FIX", "false").lower() == "true"
            )
        # 路径配置环境变量（支持绝对路径）
        if "AEROTRI_DIAGNOSTIC_AGENT_MEMORY" in os.environ:
            overrides.setdefault("diagnostic", {})["agent_memory_path"] = Path(os.getenv("AEROTRI_DIAGNOSTIC_AGENT_MEMORY"))
        if "AEROTRI_DIAGNOSTIC_HISTORY_LOG" in os.environ:
            overrides.setdefault("diagnostic", {})["history_log_path"] = Path(os.getenv("AEROTRI_DIAGNOSTIC_HISTORY_LOG"))
        if "AEROTRI_DIAGNOSTIC_CLAUDE_MD" in os.environ:
            overrides.setdefault("diagnostic", {})["claude_md_path"] = Path(os.getenv("AEROTRI_DIAGNOSTIC_CLAUDE_MD"))
        if "AEROTRI_DIAGNOSTIC_CONTEXT_DIR" in os.environ:
            overrides.setdefault("diagnostic", {})["context_output_dir"] = Path(os.getenv("AEROTRI_DIAGNOSTIC_CONTEXT_DIR"))

        # 通知服务配置
        if "AEROTRI_NOTIFICATION_ENABLED" in os.environ:
            overrides.setdefault("notification", {})["enabled"] = (
                os.getenv("AEROTRI_NOTIFICATION_ENABLED", "false").lower() == "true"
            )

        return overrides

    @classmethod
    def create(cls) -> "AppSettings":
        """
        创建配置实例，按照优先级加载配置

        优先级 (从高到低):
        1. 环境变量
        2. application.{environment}.yaml (可选)
        3. application.yaml + observability.yaml (新配置)
        """
        # backend/app/conf/settings.py -> backend/config/
        # __file__ is in backend/app/conf/, need to go up 3 levels to backend/
        config_dir = Path(__file__).resolve().parent.parent.parent / "config"

        # 检测环境
        environment = os.getenv("AEROTRI_ENV", os.getenv("ENVIRONMENT", "production"))

        # 按优先级加载 YAML 配置
        yaml_config: Dict[str, Any] = {}

        # 1. 加载 application.yaml (核心应用配置)
        application_file = config_dir / "application.yaml"
        if application_file.exists():
            app_config = cls.load_from_yaml(application_file)
            if app_config:
                # 处理 app 配置节 (添加 'app' 前缀的字段映射到顶层)
                if "app" in app_config:
                    app_section = app_config.pop("app")
                    # 映射 app 节字段到顶层
                    for key, value in app_section.items():
                        yaml_config[key] = value
                yaml_config.update(app_config)

        # 2. 加载 observability.yaml (可观测性配置)
        observability_file = config_dir / "observability.yaml"
        if observability_file.exists():
            obs_config = cls.load_from_yaml(observability_file)
            if obs_config:
                yaml_config.update(obs_config)

        # 3. 加载环境特定配置 (覆盖主配置)
        env_file = config_dir / f"application.{environment}.yaml"
        if env_file.exists():
            env_config = cls.load_from_yaml(env_file)
            yaml_config.update(env_config)

        # 4. 应用环境变量覆盖
        env_overrides = cls.load_env_overrides()
        cls._merge_dict(yaml_config, env_overrides)

        # 创建配置实例（Pydantic 支持嵌套字典）
        return cls(**yaml_config)

    @staticmethod
    def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """递归合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                AppSettings._merge_dict(base[key], value)
            else:
                base[key] = value

    @staticmethod
    def _flatten_config(config: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
        """
        展平嵌套配置字典

        例如:
        {
            "database": {"path": "./data/db"},
            "algorithms": {"colmap": {"path": "/usr/bin/colmap"}}
        }

        展平为:
        {
            "database_path": "./data/db",
            "algorithms_colmap_path": "/usr/bin/colmap"
        }
        """
        items: List[tuple[str, Any]] = []
        for k, v in config.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(AppSettings._flatten_config(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def setup_directories(self) -> None:
        """创建必要的目录"""
        self.paths.setup_directories()
        self.diagnostic.setup_directories()

    def get_absolute_paths(self) -> Dict[str, Path]:
        """
        获取所有绝对路径配置

        Returns:
            包含所有绝对路径的字典 {
                'project_root': Path,
                'data_dir': Path,
                'outputs_dir': Path,
                'blocks_dir': Path,
                'thumbnails_dir': Path,
                'database_path': Path,
                'gs_repo_path': Path
            }
        """
        return {
            'project_root': self.paths.project_root,
            'data_dir': self.paths.data_dir,
            'outputs_dir': self.paths.outputs_dir,
            'blocks_dir': self.paths.blocks_dir,
            'thumbnails_dir': self.paths.thumbnails_dir,
            'database_path': self.database.path,
            'gs_repo_path': self.gaussian_splatting.repo_path,
        }

    def validate_executables(self) -> Dict[str, List[str]]:
        """
        验证关键可执行文件是否存在

        Returns:
            缺失的可执行文件字典 {category: [missing_executables]}
        """
        missing: Dict[str, List[str]] = {}

        # 检查 COLMAP
        colmap_exe = self.algorithms.colmap.get_executable("colmap")
        if colmap_exe and not colmap_exe.exists():
            missing['colmap'] = [str(colmap_exe)]

        # 检查 GLOMAP
        glomap_exe = self.algorithms.glomap.get_executable("glomap")
        if glomap_exe and not glomap_exe.exists():
            missing['glomap'] = [str(glomap_exe)]

        # 检查 OpenMVG
        if self.algorithms.openmvg.bin_dir:
            openmvg_dir = Path(self.algorithms.openmvg.bin_dir)
            if not openmvg_dir.exists():
                missing['openmvg'] = [str(openmvg_dir)]

        # 检查 OpenMVS
        if self.algorithms.openmvs.bin_dir:
            openmvs_dir = Path(self.algorithms.openmvs.bin_dir)
            if not openmvs_dir.exists():
                missing['openmvs'] = [str(openmvs_dir)]

        # 检查 3DGS
        gs_repo = self.gaussian_splatting.repo_path
        if not gs_repo.exists():
            missing['gaussian_splatting'] = [str(gs_repo)]

        return missing


# ============================================================================
# 配置单例
# ============================================================================

_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """获取配置单例

    Returns:
        全局唯一的 AppSettings 实例
    """
    global _settings
    if _settings is None:
        _settings = AppSettings.create()
        logger.info(f"Configuration loaded (environment={_settings.environment})")
    return _settings


def reload_settings() -> AppSettings:
    """重新加载配置

    Returns:
        重新加载的 AppSettings 实例
    """
    global _settings
    _settings = AppSettings.create()
    logger.info("Configuration reloaded")
    return _settings
