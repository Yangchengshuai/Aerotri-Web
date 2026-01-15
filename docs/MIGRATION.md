# AeroTri Web 配置迁移指南

本文档帮助您从旧的配置系统迁移到新的统一配置管理系统。

## 目录

- [为什么要迁移？](#为什么要迁移)
- [迁移前准备](#迁移前准备)
- [快速迁移](#快速迁移)
- [详细迁移步骤](#详细迁移步骤)
- [环境变量对照表](#环境变量对照表)
- [验证迁移](#验证迁移)
- [回滚方案](#回滚方案)
- [常见问题](#常见问题)

---

## 为什么要迁移？

### 旧配置系统的问题

1. **硬编码路径**: 代码中包含开发者个人路径（如 `/root/work/aerotri-web`）
2. **配置分散**: 算法路径、数据库路径、输出路径分散在多个文件中
3. **不够灵活**: 修改配置需要编辑代码，不利于部署和环境切换

### 新配置系统的优势

1. ✅ **统一配置**: 所有配置集中在 YAML 配置文件和环境变量中
2. ✅ **类型安全**: 使用 Pydantic 进行配置验证
3. ✅ **优先级明确**: 环境变量 > YAML > 默认值
4. ✅ **自动验证**: 启动时自动验证关键配置
5. ✅ **完全向后兼容**: 所有旧环境变量继续工作

---

## 迁移前准备

### 1. 备份当前配置

备份您当前的环境变量和配置文件：

```bash
# 导出当前环境变量
env | grep -E "(COLMAP|GLOMAP|GS_|OPENMVG|AEROTRI|QUEUE)" > backup_env.txt

# 备份旧配置文件（如果存在）
cp backend/app/settings.py backend/app/settings.py.backup
```

### 2. 记录当前配置

检查并记录以下配置：

| 配置项 | 旧位置 | 说明 |
|--------|--------|------|
| 数据库路径 | `DATABASE_PATH` in `database.py` | SQLite 数据库文件位置 |
| 算法路径 | `app/settings.py` | COLMAP、GLOMAP 等可执行文件 |
| 3DGS 路径 | `app/settings.py` | GS_REPO_PATH, GS_PYTHON |
| 输出目录 | 硬编码 | `data/outputs` |
| 图像根路径 | 环境变量 | AEROTRI_IMAGE_ROOT |

---

## 快速迁移

### 方式 1：零配置迁移（推荐用于测试）

如果您已经使用环境变量配置，新系统会自动读取，**无需任何更改**。

```bash
# 直接启动，系统会自动读取现有环境变量
cd aerotri-web/backend
uvicorn app.main:app --reload
```

新系统会：
- ✅ 继续读取所有旧环境变量（COLMAP_PATH、GS_REPO_PATH 等）
- ✅ 使用默认配置作为后备
- ✅ 在启动时验证配置

### 方式 2：使用配置文件（推荐用于生产）

1. **复制配置示例**：
```bash
cd aerotri-web/backend
cp config/settings.yaml.example config/settings.yaml
```

2. **编辑配置文件**（参考下面的详细步骤）

3. **启动服务**：
```bash
uvicorn app.main:app --reload
```

---

## 详细迁移步骤

### 步骤 1: 迁移算法路径配置

**旧配置**（在 `app/settings.py` 中）：
```python
PROJECT_ROOT = Path("/root/work/aerotri-web")
GS_REPO_PATH = Path("/root/work/gs_workspace/gaussian-splatting")
GS_PYTHON = "/root/miniconda3/envs/gs_env_py310/bin/python"
```

**新配置方式**（三选一）：

#### 方式 A: 使用环境变量（推荐）

```bash
# 保持现有环境变量不变
export COLMAP_PATH=/usr/local/bin/colmap
export GLOMAP_PATH=/usr/local/bin/glomap
export GS_REPO_PATH=/opt/gaussian-splatting
export GS_PYTHON=/opt/gs_env/bin/python
```

#### 方式 B: 使用 YAML 配置文件

创建 `backend/config/settings.yaml`：

```yaml
algorithms:
  colmap:
    path: "/usr/local/bin/colmap"
  glomap:
    path: "/usr/local/bin/glomap"
  openmvg:
    bin_dir: "/usr/local/bin"
    sensor_db: "/usr/local/share/sensor_width_camera_database.txt"
  openmvs:
    bin_dir: "/usr/local/lib/openmvs/bin"

gaussian_splatting:
  repo_path: "/opt/gaussian-splatting"
  python: "/opt/gs_env/bin/python"
  tensorboard_path: "tensorboard"
```

#### 方式 C: 混合方式（推荐用于部署）

```bash
# YAML 文件包含默认配置
# 环境变量用于部署时覆盖特定路径
export COLMAP_PATH=/custom/path/to/colmap
```

### 步骤 2: 迁移数据库路径配置

**旧配置**：
```python
# app/models/database.py
DATABASE_PATH = "/root/work/aerotri-web/data/aerotri.db"
```

**新配置方式**：

#### 方式 A: 环境变量
```bash
export AEROTRI_DB_PATH=/var/lib/aerotri/aerotri.db
```

#### 方式 B: YAML 配置文件
```yaml
# config/settings.yaml
database:
  path: "/var/lib/aerotri/aerotri.db"
  pool_size: 5
```

### 步骤 3: 迁移图像根路径配置

**旧配置**：
```bash
export AEROTRI_IMAGE_ROOT=/mnt/work_odm/chengshuai
```

**新配置方式**（支持多路径）：

#### 方式 A: 环境变量（推荐）
```bash
# 多个路径用冒号分隔
export AEROTRI_IMAGE_ROOTS=/data/images:/mnt/storage:/home/user/images

# 或使用单个路径（向后兼容）
export AEROTRI_IMAGE_ROOT=/data/images
```

#### 方式 B: 独立 YAML 文件
创建 `backend/config/image_roots.yaml`：
```yaml
image_roots:
  - name: "项目数据"
    path: "/data/projects"
  - name: "NAS 存储"
    path: "/mnt/nas/images"
```

#### 方式 C: 在 settings.yaml 中配置
```yaml
# config/settings.yaml
image_roots:
  paths:
    - name: "本地"
      path: "/data/images"
    - name: "NAS"
      path: "/mnt/storage"
```

### 步骤 4: 迁移队列配置

**旧配置**：
```bash
export QUEUE_MAX_CONCURRENT=1
```

**新配置方式**：

#### 方式 A: 环境变量（保持不变）
```bash
export QUEUE_MAX_CONCURRENT=2
```

#### 方式 B: YAML 配置文件
```yaml
# config/settings.yaml
queue:
  max_concurrent: 2
  scheduler_interval: 5
```

### 步骤 5: 多环境配置（可选）

为不同环境创建独立配置：

**开发环境** (`config/settings.development.yaml`)：
```yaml
app:
  debug: true
  environment: development
  log_level: DEBUG

paths:
  data_dir: "./dev_data"

algorithms:
  colmap:
    path: "/usr/local/bin/colmap"
```

**生产环境** (`config/settings.production.yaml`)：
```yaml
app:
  debug: false
  environment: production
  log_level: WARNING

paths:
  data_dir: "/var/lib/aerotri/data"

queue:
  max_concurrent: 4
```

激活环境：
```bash
# 开发环境
export AEROTRI_ENV=development
uvicorn app.main:app --reload

# 生产环境
export AEROTRI_ENV=production
uvicorn app.main:app
```

---

## 环境变量对照表

### 完全兼容的环境变量（无需更改）

| 旧环境变量 | 新系统支持 | 说明 |
|-----------|-----------|------|
| `COLMAP_PATH` | ✅ | COLMAP 可执行文件路径 |
| `GLOMAP_PATH` | ✅ | GLOMAP 可执行文件路径 |
| `INSTANTSFM_PATH` | ✅ | InstantSfM 可执行文件路径 |
| `OPENMVG_BIN_DIR` | ✅ | OpenMVG 二进制目录 |
| `OPENMVG_SENSOR_DB` | ✅ | 相机传感器数据库 |
| `OPENMVS_BIN_DIR` | ✅ | OpenMVS 二进制目录 |
| `GS_REPO_PATH` | ✅ | 3DGS 仓库路径 |
| `GS_PYTHON` | ✅ | 3DGS Python 解释器 |
| `TENSORBOARD_PATH` | ✅ | TensorBoard 可执行文件 |
| `SPZ_PYTHON` | ✅ | SPZ Python 环境 |
| `AEROTRI_IMAGE_ROOT` | ✅ | 图像根路径（单个） |
| `AEROTRI_IMAGE_ROOTS` | ✅ | 图像根路径（多个） |
| `AEROTRI_DB_PATH` | ✅ | 数据库路径 |
| `QUEUE_MAX_CONCURRENT` | ✅ | 队列最大并发数 |

### 新增环境变量（可选）

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `AEROTRI_ENV` | `production` | 运行环境（development/production） |
| `AEROTRI_DEBUG` | `false` | 调试模式 |
| `AEROTRI_LOG_LEVEL` | `INFO` | 日志级别 |
| `AEROTRI_PATH_DATA_DIR` | `./data` | 数据目录 |
| `AEROTRI_PATH_OUTPUTS_DIR` | `./data/outputs` | 输出目录 |

### 移除的硬编码（无需配置）

以下路径从新配置系统移除，不再需要手动配置：

- ❌ `PROJECT_ROOT` - 自动检测
- ❌ `/root/work/aerotri-web` - 相对路径自动解析
- ❌ `OPENMVS_INTERFACE_COLMAP_PATH` - 自动构建
- ❌ `OPENMVS_DENSIFY_PATH` - 自动构建
- ❌ `OPENMVS_RECONSTRUCT_PATH` - 自动构建
- ❌ `OPENMVS_REFINE_PATH` - 自动构建
- ❌ `OPENMVS_TEXTURE_PATH` - 自动构建

---

## 验证迁移

### 1. 启动时验证

新系统会在启动时自动验证配置：

```bash
cd aerotri-web/backend
uvicorn app.main:app
```

查看日志输出：
```
INFO:     Loaded config from: /path/to/config/defaults.yaml
INFO:     Loaded config from: /path/to/config/settings.yaml
WARNING:  Algorithm executable not found: colmap (this is OK if in PATH)
INFO:     Created directory: /path/to/data/outputs
INFO:     Configuration validation complete
```

### 2. 手动验证脚本

创建测试脚本 `test_config.py`：

```python
from app.conf.settings import get_settings
from app.conf.validation import validate_on_startup

# 读取配置
settings = get_settings()

# 打印关键配置
print(f"Database: {settings.database.path}")
print(f"Outputs Dir: {settings.paths.outputs_dir}")
print(f"COLMAP: {settings.algorithms.colmap.path}")
print(f"GS Repo: {settings.gaussian_splatting.repo_path}")

# 验证配置
warnings = validate_on_startup()
if warnings:
    print("Warnings:")
    for w in warnings:
        print(f"  - {w}")
else:
    print("✅ Configuration is valid!")
```

运行：
```bash
python test_config.py
```

### 3. 运行测试套件

```bash
cd aerotri-web/backend
pytest tests/test_config.py -v
pytest tests/test_algorithm_integration.py -v
pytest tests/test_core_paths_integration.py -v
pytest tests/test_output_paths_integration.py -v
```

所有测试应该通过（80 个测试用例）。

---

## 回滚方案

如果迁移后出现问题，可以回滚到旧配置系统：

### 方式 1: 紧急回滚（使用旧代码）

```bash
# 切换到迁移前的 commit
git checkout <commit-hash-before-migration>

# 或直接恢复备份的文件
cp backend/app/settings.py.backup backend/app/settings.py
```

### 方式 2: 保留新代码，使用旧配置方式

新系统完全向后兼容，可以继续使用环境变量配置：

```bash
# 只使用环境变量，不创建 YAML 配置文件
export COLMAP_PATH=/usr/local/bin/colmap
export GS_REPO_PATH=/opt/gaussian-splatting
export AEROTRI_DB_PATH=/var/lib/aerotri/aerotri.db

# 系统会使用默认配置 + 环境变量覆盖
uvicorn app.main:app
```

### 方式 3: 部分回滚

如果某个特定配置有问题，可以只修改那部分：

```yaml
# config/settings.yaml
# 只配置有问题的部分，其他使用默认值
algorithms:
  colmap:
    path: "/custom/path/to/colmap"  # 只修改这一项
```

---

## 常见问题

### Q1: 迁移后我的旧环境变量还有效吗？

**A**: 是的！新系统完全向后兼容。所有旧环境变量（`COLMAP_PATH`、`GS_REPO_PATH` 等）继续工作，优先级高于 YAML 配置。

### Q2: 我是否必须创建 YAML 配置文件？

**A**: 不必须。如果您已经使用环境变量配置，可以直接继续使用，无需创建任何 YAML 文件。新系统会自动使用合理的默认值。

### Q3: 如何知道哪个配置生效了？

**A**: 查看启动日志，系统会输出加载的配置文件。您也可以运行验证脚本：

```python
from app.conf.settings import get_settings
settings = get_settings()
print(settings.model_dump_json(indent=2))
```

### Q4: 配置文件修改后需要重启吗？

**A**: 是的。配置文件修改后需要重启服务才能生效。环境变量修改也需要重启。

### Q5: 如何在不同环境使用不同配置？

**A**: 创建环境特定配置文件（如 `settings.development.yaml`、`settings.production.yaml`），然后通过 `AEROTRI_ENV` 环境变量激活。

### Q6: 相对路径和绝对路径如何选择？

**A**:
- **开发环境**: 推荐使用相对路径（如 `./data`），便于在不同机器上开发
- **生产环境**: 推荐使用绝对路径（如 `/var/lib/aerotri/data`），更明确
- **Docker 环境**: 推荐使用绝对路径

新系统会自动将相对路径解析为绝对路径。

### Q7: 我该如何配置多个图像存储位置？

**A**: 有三种方式：

**方式 1**: 环境变量（冒号分隔）
```bash
export AEROTRI_IMAGE_ROOTS=/data/images:/mnt/storage:/home/user/images
```

**方式 2**: 独立 YAML 文件
```yaml
# config/image_roots.yaml
image_roots:
  - name: "本地存储"
    path: "/data/images"
  - name: "NAS 存储"
    path: "/mnt/storage"
```

**方式 3**: settings.yaml
```yaml
image_roots:
  paths:
    - name: "本地"
      path: "/data/images"
    - name: "NAS"
      path: "/mnt/storage"
```

### Q8: 迁移会影响我的数据吗？

**A**: 不会。迁移只影响配置方式，不会修改或移动任何数据文件。数据库、输出目录、图像文件都保持不变。

### Q9: 如何验证迁移是否成功？

**A**: 运行测试套件：
```bash
pytest tests/ -v
```

所有 80 个测试应该通过。如果测试失败，请查看具体错误信息。

### Q10: 迁移后性能会受影响吗？

**A**: 不会。新配置系统在启动时加载一次配置，运行时性能与旧系统完全相同。

---

## 迁移检查清单

使用此清单确保迁移完整：

- [ ] 备份了当前配置（环境变量、配置文件）
- [ ] 记录了当前数据库路径
- [ ] 记录了当前算法路径（COLMAP、GLOMAP 等）
- [ ] 记录了当前 3DGS 配置（GS_REPO_PATH、GS_PYTHON）
- [ ] 记录了当前图像根路径
- [ ] 测试了新配置系统启动
- [ ] 验证了算法路径正确
- [ ] 验证了数据库路径正确
- [ ] 验证了图像根路径正确
- [ ] 运行了测试套件并全部通过
- [ ] 更新了部署文档（如需要）

---

## 下一步

迁移完成后，建议：

1. **阅读完整配置文档**: [CONFIGURATION.md](CONFIGURATION.md)
2. **优化配置**: 根据实际部署环境调整配置
3. **设置多环境配置**: 为开发、测试、生产创建独立配置
4. **更新部署脚本**: 将新的配置方式集成到部署流程中

---

## 获取帮助

如有迁移问题：

1. 查看 [CONFIGURATION.md](CONFIGURATION.md) 了解配置系统详情
2. 查看启动日志中的警告和错误信息
3. 运行测试套件验证配置
4. 提交 GitHub Issue 描述问题

---

**迁移完成后，您的 AeroTri Web 系统将拥有更灵活、更安全、更易维护的配置管理！** 🎉
