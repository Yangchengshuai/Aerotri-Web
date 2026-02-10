# 配置系统迁移清单 (Configuration System Migration Checklist)

**迁移目标**: 将所有模块从旧的 `app.settings` 迁移到新的 `app.conf.settings` 配置系统

**新配置系统特点**:
- 使用 Pydantic Settings 实现类型安全
- 支持 YAML 配置文件 (defaults.yaml, settings.yaml)
- 环境变量覆盖
- 配置验证和默认值
- 路径自动解析

---

## 已迁移文件 ✅

### 配置层 (Configuration Layer)
- [x] `app/conf/settings.py` - 新配置系统核心实现
- [x] `app/conf/validation.py` - 配置验证功能

### 数据层 (Data Layer)
- [x] `app/models/database.py` - 使用 `get_settings()` 获取数据库配置

### 服务层 (Service Layer)
- [x] `app/services/task_runner.py` - 使用 `get_settings()` 获取算法路径
- [x] `app/services/gs_runner.py` - 使用 `get_settings()` 获取 3DGS 配置
- [x] `app/services/tiles_runner.py` - 使用 `get_settings()` 获取路径配置
- [x] `app/services/openmvs_runner.py` - 使用 `get_settings()` 获取 OpenMVS 配置
- [x] `app/services/image_service.py` - 使用 `get_settings()` 获取路径配置
- [x] `app/services/workspace_service.py` - 使用 `get_settings()` 获取路径配置

---

## 需要迁移的文件 📋

### 高优先级 (High Priority)

#### 服务层 (Service Layer)
- [ ] **`app/services/spz_loader.py`**
  - 当前导入: `from ..settings import SPZ_PYTHON`
  - 需要改为: `from ..conf.settings import get_settings`
  - 影响范围: SPZ 压缩功能
  - 迁移步骤:
    1. 修改导入语句
    2. 更新 `get_spz_python_path()` 函数使用 `settings.spz.python`
    3. 测试 SPZ 文件加载功能

---

## 待检查的文件 🔍

### API 层 (API Layer)
需要检查以下文件是否有隐式配置使用:
- [ ] `app/api/blocks.py` - Block 管理 API
- [ ] `app/api/reconstruction.py` - 重建 API
- [ ] `app/api/gs.py` - 3DGS API
- [ ] `app/api/tiles.py` - 3D Tiles API
- [ ] `app/api/system.py` - 系统配置 API
- [ ] `app/api/unified_tasks.py` - 统一任务 API

### WebSocket 层 (WebSocket Layer)
- [ ] `app/ws/progress.py` - 进度推送
- [ ] `app/ws/visualization.py` - 可视化推送

### 其他服务 (Other Services)
- [ ] `app/services/gpu_service.py` - GPU 监控服务
- [ ] `app/services/queue_scheduler.py` - 队列调度
- [ ] `app/services/notification/` - 通知服务
- [ ] `app/main.py` - 应用入口 (已集成配置验证)

### 工具脚本 (Utility Scripts)
- [ ] `app/services/openclaw_diagnostic_agent.py` - 诊断代理
- [ ] `tools/*.py` - 工具脚本 (如果有)

---

## 配置映射关系 (Configuration Mapping)

### 旧配置 (`app/settings.py`) → 新配置 (`app.conf.settings`)

| 旧配置常量 | 新配置路径 | 说明 |
|-----------|----------|------|
| `PROJECT_ROOT` | `settings.paths.project_root` | 项目根目录 |
| `OPENMVS_BIN_DIR` | `settings.algorithms.openmvs.bin_dir` | OpenMVS 二进制目录 |
| `OPENMVS_INTERFACE_COLMAP` | `settings.algorithms.openmvs.bin_dir + "/InterfaceCOLMAP"` | InterfaceCOLMAP 路径 |
| `OPENMVS_DENSIFY` | `settings.algorithms.openmvs.bin_dir + "/DensifyPointCloud"` | Densify 路径 |
| `OPENMVS_RECONSTRUCT` | `settings.algorithms.openmvs.bin_dir + "/ReconstructMesh"` | ReconstructMesh 路径 |
| `OPENMVS_REFINE` | `settings.algorithms.openmvs.bin_dir + "/RefineMesh"` | RefineMesh 路径 |
| `OPENMVS_TEXTURE` | `settings.algorithms.openmvs.bin_dir + "/TextureMesh"` | TextureMesh 路径 |
| `GS_REPO_PATH` | `settings.gaussian_splatting.repo_path` | 3DGS 仓库路径 |
| `GS_PYTHON` | `settings.gaussian_splatting.python` | 3DGS Python 解释器 |
| `TENSORBOARD_PATH` | `settings.gaussian_splatting.tensorboard_path` | TensorBoard 路径 |
| `TENSORBOARD_PORT_START` | `settings.gaussian_splatting.tensorboard_port_start` | TensorBoard 起始端口 |
| `TENSORBOARD_PORT_END` | `settings.gaussian_splatting.tensorboard_port_end` | TensorBoard 结束端口 |
| `NETWORK_GUI_PORT_START` | `settings.gaussian_splatting.network_gui_port_start` | Network GUI 起始端口 |
| `NETWORK_GUI_PORT_END` | `settings.gaussian_splatting.network_gui_port_end` | Network GUI 结束端口 |
| `NETWORK_GUI_IP` | `settings.gaussian_splatting.network_gui_ip` | Network GUI IP |
| `SPZ_PYTHON` | `settings.spz.python` | SPZ Python 解释器 |

---

## 迁移步骤 (Migration Steps)

### 标准迁移流程 (Standard Migration Process)

#### 1. 更新导入语句
```python
# 旧代码
from ..settings import SOME_CONSTANT
from app.settings import SOME_CONSTANT

# 新代码
from ..conf.settings import get_settings

settings = get_settings()
value = settings.some_section.some_field
```

#### 2. 更新配置访问方式
```python
# 旧代码 - 直接使用常量
from ..settings import SPZ_PYTHON
spz_python = SPZ_PYTHON

# 新代码 - 通过配置对象
from ..conf.settings import get_settings
settings = get_settings()
spz_python = settings.spz.python
```

#### 3. 更新路径操作
```python
# 旧代码
from ..settings import GS_REPO_PATH
repo_path = GS_REPO_PATH / "train.py"

# 新代码
from ..conf.settings import get_settings
settings = get_settings()
repo_path = settings.gaussian_splatting.repo_path / "train.py"
```

#### 4. 测试验证
- 运行单元测试: `pytest`
- 启动服务: `uvicorn app.main:app --reload`
- 检查日志确认配置加载正确
- 验证功能正常工作

#### 5. 提交代码
```bash
git add app/services/<filename>.py
git commit -m "refactor(config): migrate <filename> to new config system"
```

---

## 特殊注意事项 (Special Notes)

### 1. SPZ_LOADER 特殊处理
`spz_loader.py` 需要特殊处理，因为它在模块级别导入常量:

**当前代码**:
```python
from ..settings import SPZ_PYTHON

def get_spz_python_path() -> Optional[str]:
    spz_python = Path(SPZ_PYTHON)
    ...
```

**修改后**:
```python
from ..conf.settings import get_settings

def get_spz_python_path() -> Optional[str]:
    settings = get_settings()
    spz_python = Path(settings.spz.python)
    ...
```

### 2. OpenMVS 路径构建
OpenMVS 有多个可执行文件，需要从 `bin_dir` 构建:

**当前代码** (已迁移):
```python
settings = get_settings()
openmvs_bin = settings.algorithms.openmvs.bin_dir
densify_path = Path(openmvs_bin) / "DensifyPointCloud"
```

### 3. 环境变量兼容性
新配置系统完全兼容现有环境变量，无需修改 `.env` 或启动脚本。

---

## 验证清单 (Verification Checklist)

### 配置加载验证
- [ ] 启动时无配置错误
- [ ] 日志显示 "Configuration loaded (environment=production)"
- [ ] 所有路径正确解析 (绝对路径)
- [ ] 环境变量正确覆盖配置

### 功能验证
- [ ] COLMAP 任务正常运行
- [ ] GLOMAP 任务正常运行
- [ ] InstantSfM 任务正常运行
- [ ] OpenMVG 任务正常运行
- [ ] OpenMVS 重建正常运行
- [ ] 3DGS 训练正常运行
- [ ] 3D Tiles 转换正常运行
- [ ] SPZ 压缩功能正常 (如果已配置)

### API 验证
- [ ] `/api/system/config` 返回完整配置
- [ ] `/api/system/validate` 返回验证结果
- [ ] 所有 API 端点正常响应

---

## 清理阶段 (Cleanup Phase)

迁移完成后，需要删除旧配置系统:

### 1. 删除旧配置文件
```bash
rm app/settings.py
git rm app/settings.py
```

### 2. 检查残留引用
```bash
cd backend
grep -r "from app\.settings import" app/
grep -r "from \.settings import" app/ | grep -v "conf/settings"
```

### 3. 更新文档
- [ ] 更新 README.md 中的配置说明
- [ ] 更新 CLAUDE.md 中的环境变量说明
- [ ] 创建配置指南 (CONFIG_GUIDE.md)

### 4. 最终提交
```bash
git add -A
git commit -m "refactor(config): complete migration to new config system

- Remove old app.settings module
- All modules now use app.conf.settings
- Update documentation
- Add configuration guide"
```

---

## 时间估计 (Time Estimate)

| 任务 | 预计时间 |
|-----|---------|
| 迁移 `spz_loader.py` | 15 分钟 |
| 检查 API 层文件 | 30 分钟 |
| 检查 WebSocket 层 | 15 分钟 |
| 检查其他服务 | 30 分钟 |
| 功能测试 | 1 小时 |
| 清理旧配置 | 15 分钟 |
| 更新文档 | 30 分钟 |
| **总计** | **~3 小时** |

---

## 参考资料 (References)

- **新配置系统**: `app/conf/settings.py`
- **配置验证**: `app/conf/validation.py`
- **默认配置**: `config/defaults.yaml`
- **配置示例**: `config/settings.yaml.example`
- **主应用集成**: `app/main.py` (lifespan 函数)

---

**创建时间**: 2026-02-10
**状态**: 🟡 进行中 (In Progress)
**下一步**: 迁移 `app/services/spz_loader.py`
