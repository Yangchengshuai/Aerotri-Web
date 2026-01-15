# AeroTri Web 配置指南

本文档提供 AeroTri Web 配置系统的完整使用指南。

## 目录

- [快速开始](#快速开始)
- [配置文件](#配置文件)
- [环境变量](#环境变量)
- [配置优先级](#配置优先级)
- [配置分类详解](#配置分类详解)
- [多环境配置](#多环境配置)
- [Docker 部署](#docker-部署)
- [常见问题](#常见问题)

---

## 快速开始

### 最小配置

AeroTri Web 可以在不创建任何配置文件的情况下启动，使用默认配置：

```bash
cd aerotri-web/backend
uvicorn app.main:app --reload
```

这将使用以下默认配置：
- 数据库：`./data/aerotri.db`
- 输出目录：`./data/outputs/`
- 算法路径：假设在系统 `PATH` 中（如 `colmap`、`glomap`）

### 自定义配置

有两种方式自定义配置：

#### 方式 1：环境变量（推荐用于部署）

```bash
export COLMAP_PATH=/usr/local/bin/colmap
export AEROTRI_IMAGE_ROOT=/mnt/data/images
export AEROTRI_DB_PATH=/var/lib/aerotri/aerotri.db
uvicorn app.main:app
```

#### 方式 2：配置文件（推荐用于开发）

1. 复制配置示例：
```bash
cp backend/config/settings.yaml.example backend/config/settings.yaml
```

2. 编辑配置文件：
```yaml
paths:
  data_dir: "./data"
  outputs_dir: "./data/outputs"

algorithms:
  colmap:
    path: "/usr/local/bin/colmap"
```

3. 启动服务：
```bash
uvicorn app.main:app
```

---

## 配置文件

### 配置文件位置

配置文件位于 `backend/config/` 目录：

```
backend/config/
├── defaults.yaml              # 默认配置（最低优先级）
├── settings.yaml.example       # 配置示例（复制并修改为 settings.yaml）
├── settings.yaml              # 主配置文件（用户配置）
├── settings.development.yaml   # 开发环境配置（可选）
├── settings.production.yaml    # 生产环境配置（可选）
├── image_roots.yaml           # 图像根路径配置
└── notification.yaml          # 通知服务配置
```

### 配置文件结构

#### 主配置文件：`settings.yaml`

```yaml
# 应用配置
app:
  debug: false
  environment: production
  log_level: INFO

# 路径配置
paths:
  data_dir: "./data"              # 相对于 backend/（自动解析为绝对路径）
  outputs_dir: "./data/outputs"
  blocks_dir: "./data/blocks"
  thumbnails_dir: "./data/thumbnails"

# 数据库配置
database:
  path: "./data/aerotri.db"
  pool_size: 5

# 算法配置
algorithms:
  colmap:
    path: "colmap"                # 或 "/usr/local/bin/colmap"
  glomap:
    path: "glomap"
  openmvg:
    bin_dir: "/usr/local/bin"
  openmvs:
    bin_dir: "/usr/local/lib/openmvs/bin"

# 3D Gaussian Splatting
gaussian_splatting:
  repo_path: "/opt/gaussian-splatting"
  python: "python"

# 图像根路径
image_roots:
  default: "./data/images"
```

#### 环境特定配置

创建 `settings.{environment}.yaml` 用于不同环境：

**开发环境** (`settings.development.yaml`):
```yaml
app:
  debug: true
  environment: development
  log_level: DEBUG

paths:
  data_dir: "./data"
```

**生产环境** (`settings.production.yaml`):
```yaml
app:
  debug: false
  environment: production
  log_level: WARNING

paths:
  data_dir: "/var/lib/aerotri/data"
  outputs_dir: "/var/lib/aerotri/outputs"
```

---

## 环境变量

### 核心环境变量

#### 应用配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `AEROTRI_ENV` | string | `production` | 运行环境（development/production） |
| `AEROTRI_DEBUG` | boolean | `false` | 调试模式 |
| `AEROTRI_LOG_LEVEL` | string | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `AEROTRI_FRONTEND_ORIGIN` | string | - | CORS 前端源（如 `http://localhost:3000`） |

#### 路径配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `AEROTRI_DB_PATH` | path | `./data/aerotri.db` | 数据库文件路径 |
| `AEROTRI_PATH_DATA_DIR` | path | `./data` | 数据目录 |
| `AEROTRI_PATH_OUTPUTS_DIR` | path | `./data/outputs` | 任务输出目录 |

#### 算法路径

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `COLMAP_PATH` | `colmap` | COLMAP 可执行文件路径 |
| `GLOMAP_PATH` | `glomap` | GLOMAP 可执行文件路径 |
| `INSTANTSFM_PATH` | `ins-sfm` | InstantSfM 可执行文件路径 |
| `OPENMVG_BIN_DIR` | `/usr/local/bin` | OpenMVG 二进制目录 |
| `OPENMVG_SENSOR_DB` | `/usr/local/share/sensor_width_camera_database.txt` | 相机传感器数据库 |
| `OPENMVS_BIN_DIR` | `/usr/local/lib/openmvs/bin` | OpenMVS 二进制目录 |

#### 3D Gaussian Splatting

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GS_REPO_PATH` | `/opt/gaussian-splatting` | 3DGS 仓库路径 |
| `GS_PYTHON` | `python` | 3DGS Python 解释器 |
| `TENSORBOARD_PATH` | `tensorboard` | TensorBoard 可执行文件 |
| `TENSORBOARD_PORT_START` | `6006` | TensorBoard 端口范围起始 |
| `TENSORBOARD_PORT_END` | `6100` | TensorBoard 端口范围结束 |
| `NETWORK_GUI_IP` | `127.0.0.1` | 网络 GUI IP 地址 |
| `NETWORK_GUI_PORT_START` | `6009` | 网络 GUI 端口范围起始 |
| `NETWORK_GUI_PORT_END` | `6109` | 网络 GUI 端口范围结束 |

#### SPZ 压缩

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SPZ_PYTHON` | `python` | SPZ Python 解释器 |

#### 图像路径

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `AEROTRI_IMAGE_ROOT` | string | `./data/images` | 单个图像根路径（向后兼容） |
| `AEROTRI_IMAGE_ROOTS` | string | - | 多个图像根路径（冒号分隔） |

#### 队列配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `QUEUE_MAX_CONCURRENT` | integer | `1` | 队列最大并发任务数（范围：1-10） |

---

## 配置优先级

配置优先级从高到低：

1. **环境变量** - 最高优先级，用于部署覆盖
2. **settings.{environment}.yaml** - 环境特定配置（如 `settings.development.yaml`）
3. **settings.yaml** - 主配置文件
4. **defaults.yaml** - 默认配置（最低优先级）

### 优先级示例

```yaml
# defaults.yaml
app:
  debug: false

# settings.yaml
app:
  debug: true

# settings.development.yaml
app:
  debug: true

# 环境变量
export AEROTRI_DEBUG=false
```

最终生效：`AEROTRI_DEBUG=false`（环境变量优先级最高）

---

## 配置分类详解

### 1. 应用配置

```yaml
app:
  name: "AeroTri Web"           # 应用名称
  version: "1.0.0"              # 应用版本
  debug: false                 # 调试模式
  environment: production       # 运行环境
  log_level: INFO              # 日志级别
  cors_origins:                # CORS 允许的前端源
    - "http://localhost:3000"
```

### 2. 路径配置

```yaml
paths:
  data_dir: "./data"            # 数据目录（相对路径自动解析为绝对路径）
  outputs_dir: "./data/outputs" # 任务输出目录
  blocks_dir: "./data/blocks"   # Block 工作目录
  thumbnails_dir: "./data/thumbnails"  # 缩略图缓存
```

**路径解析规则**：

配置系统自动检测项目根目录为 `backend/`，并按以下规则解析路径：

| 配置值 | 类型 | 解析后路径（示例） |
|--------|------|-------------------|
| `./data` | 相对路径 | `/path/to/aerotri-web/backend/data` |
| `data` | 相对路径 | `/path/to/aerotri-web/backend/data` |
| `/var/lib/aerotri/data` | 绝对路径 | `/var/lib/aerotri/data`（保持不变） |
| `../shared` | 向上相对 | `/path/to/aerotri-web/shared` |

**重要说明**：
- 所有相对路径都相对于 `backend/` 目录
- 配置系统会自动检测 `backend/` 目录作为项目根目录
- 相对路径在启动时自动解析为绝对路径
- 推荐使用相对路径以支持不同部署环境
- 如果需要在 `backend/` 之外存储数据，使用绝对路径或向上相对路径（如 `../shared`）

### 3. 数据库配置

```yaml
database:
  path: "./data/aerotri.db"     # 数据库文件路径
  pool_size: 5                  # 连接池大小
  max_overflow: 10              # 最大溢出连接数
```

### 4. 算法配置

```yaml
algorithms:
  colmap:
    path: "colmap"              # 可执行文件路径（从 PATH 查找）
    # 或使用绝对路径：path: "/usr/local/bin/colmap"

  glomap:
    path: "glomap"

  instantsfm:
    path: "ins-sfm"             # 通常在 conda 环境的 PATH 中

  openmvg:
    bin_dir: "/usr/local/bin"   # OpenMVG 二进制目录
    sensor_db: "/usr/local/share/sensor_width_camera_database.txt"

  openmvs:
    bin_dir: "/usr/local/lib/openmvs/bin"
```

### 5. 3D Gaussian Splatting 配置

```yaml
gaussian_splatting:
  repo_path: "/opt/gaussian-splatting"
  python: "python"
  tensorboard_path: "tensorboard"
  tensorboard_port_start: 6006
  tensorboard_port_end: 6100
  network_gui_ip: "127.0.0.1"
  network_gui_port_start: 6009
  network_gui_port_end: 6109
```

### 6. 图像根路径配置

#### 方式 1：在 `settings.yaml` 中配置

```yaml
image_roots:
  default: "./data/images"
  paths:
    - name: "本地数据"
      path: "./data/images"
    - name: "外部存储"
      path: "/mnt/storage"
```

#### 方式 2：使用独立的 `image_roots.yaml`

```yaml
# backend/config/image_roots.yaml
image_roots:
  - name: "项目数据"
    path: "/data/projects"
  - name: "NAS 存储"
    path: "/mnt/nas/images"
```

#### 方式 3：使用环境变量

```bash
# 单个路径（向后兼容）
export AEROTRI_IMAGE_ROOT=/mnt/data/images

# 多个路径
export AEROTRI_IMAGE_ROOTS=/mnt/data/images:/mnt/storage:/home/user/images
```

### 7. 队列配置

```yaml
queue:
  max_concurrent: 1              # 最大并发任务数
  scheduler_interval: 5         # 调度器轮询间隔（秒）
```

### 8. GPU 配置

```yaml
gpu:
  monitor_interval: 2           # GPU 监控间隔（秒）
  auto_selection: "most_free"   # 自动选择策略
```

---

## 多环境配置

### 开发环境

创建 `backend/config/settings.development.yaml`：

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

设置环境变量激活：
```bash
export AEROTRI_ENV=development
uvicorn app.main:app --reload
```

### 生产环境

创建 `backend/config/settings.production.yaml`：

```yaml
app:
  debug: false
  environment: production
  log_level: WARNING

paths:
  data_dir: "/var/lib/aerotri/data"
  outputs_dir: "/var/lib/aerotri/outputs"

queue:
  max_concurrent: 4
```

设置环境变量激活：
```bash
export AEROTRI_ENV=production
uvicorn app.main:app
```

---

## Docker 部署

### 使用环境变量

```dockerfile
FROM aerotri-web:latest

ENV COLMAP_PATH=/usr/local/bin/colmap
ENV AEROTRI_IMAGE_ROOT=/data/images
ENV AEROTRI_DB_PATH=/data/aerotri.db
ENV QUEUE_MAX_CONCURRENT=2

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### 使用 docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    image: aerotri-web:latest
    environment:
      # 应用配置
      - AEROTRI_ENV=production
      - AEROTRI_DEBUG=false

      # 路径配置
      - AEROTRI_DB_PATH=/data/aerotri.db
      - AEROTRI_IMAGE_ROOTS=/data/images:/mnt/storage

      # 算法路径
      - COLMAP_PATH=/usr/local/bin/colmap
      - GLOMAP_PATH=/usr/local/bin/glomap
      - GS_REPO_PATH=/opt/gaussian-splatting
      - GS_PYTHON=/opt/gs_env/bin/python

      # 队列配置
      - QUEUE_MAX_CONCURRENT=2

    volumes:
      - ./data:/data
      - /mnt/images:/data/images:ro
      - /mnt/storage:/mnt/storage:ro

    ports:
      - "8000:8000"
```

---

## 常见问题

### Q1: 如何验证配置是否正确？

A: 启动时系统会自动验证配置，错误和警告会输出到日志。你也可以手动验证：

```python
from app.conf.settings import get_settings
from app.conf.validation import validate_on_startup

settings = get_settings()
warnings = validate_on_startup()
```

### Q2: 配置文件修改后需要重启吗？

A: 是的，配置文件修改后需要重启服务。环境变量修改也需要重启。

### Q3: 如何查看当前生效的配置？

A: 查看日志输出，或使用配置验证功能。配置系统会在启动时输出加载的配置文件。

### Q4: 相对路径和绝对路径如何选择？

A:
- **开发环境**：推荐使用相对路径（如 `./data`）
- **生产环境**：推荐使用绝对路径（如 `/var/lib/aerotri/data`）
- **Docker 环境**：推荐使用绝对路径

### Q5: 如何迁移旧的配置？

A: 请参考 [MIGRATION.md](MIGRATION.md) 文档。

### Q6: 算法可执行文件找不到怎么办？

A: 检查以下几点：
1. 算法是否已安装：`which colmap`
2. 使用完整路径：在配置文件中指定绝对路径
3. 设置环境变量：`export COLMAP_PATH=/usr/local/bin/colmap`

### Q7: 如何配置多个图像存储位置？

A: 有三种方式：

**方式 1**：环境变量（冒号分隔）
```bash
export AEROTRI_IMAGE_ROOTS=/data/images:/mnt/storage:/home/user/images
```

**方式 2**：配置文件
```yaml
# image_roots.yaml
image_roots:
  - name: "本地存储"
    path: "/data/images"
  - name: "NAS 存储"
    path: "/mnt/storage"
```

**方式 3**：settings.yaml
```yaml
image_roots:
  paths:
    - name: "本地"
      path: "/data/images"
    - name: "NAS"
      path: "/mnt/storage"
```

### Q8: 数据库路径如何配置？

A: 三种方式：

1. **环境变量**（推荐）：
```bash
export AEROTRI_DB_PATH=/custom/path/aerotri.db
```

2. **配置文件**：
```yaml
# settings.yaml
database:
  path: "/custom/path/aerotri.db"
```

3. **默认值**：
不配置时使用 `./data/aerotri.db`

### Q9: 如何启用调试模式？

A: 设置环境变量或配置文件：

```bash
export AEROTRI_DEBUG=true
```

或：

```yaml
# settings.yaml
app:
  debug: true
```

### Q10: 3DGS 训练如何配置 Python 环境？

A: 指定包含 CUDA 扩展的 Python 解释器：

```bash
export GS_PYTHON=/opt/gs_env/bin/python
```

或：

```yaml
gaussian_splatting:
  python: "/opt/gs_env/bin/python"
```

### Q11: 配置文件路径不正确怎么办？

A: 如果遇到配置文件未加载的问题，检查以下几点：

1. **确认配置文件位置**：配置文件必须在 `backend/config/` 目录下
   ```bash
   ls -la backend/config/settings.yaml
   ```

2. **检查 YAML 语法**：使用 YAML 验证工具检查语法错误
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('backend/config/settings.yaml'))"
   ```

3. **查看启动日志**：配置系统会输出加载的配置文件
   ```
   INFO: Loaded config from: /path/to/backend/config/defaults.yaml
   INFO: Loaded config from: /path/to/backend/config/settings.yaml
   ```

4. **验证配置生效**：使用 Python 验证
   ```python
   from app.conf.settings import get_settings
   settings = get_settings()
   print(f"数据库路径: {settings.database.path}")
   ```

### Q12: 如何调试配置问题？

A: 启用调试日志查看详细的配置加载过程：

```bash
# 设置日志级别为 DEBUG
export AEROTRI_LOG_LEVEL=DEBUG

# 启动后端
cd backend
uvicorn app.main:app --reload
```

日志会显示：
- 加载的配置文件路径
- 配置合并过程
- 最终生效的配置值

---

## 配置故障排除

### 问题1: 配置文件不生效

**症状**: 修改了 `settings.yaml`，但配置没有生效

**可能原因**:
1. 配置文件路径错误（必须在 `backend/config/` 目录）
2. YAML 语法错误
3. 环境变量覆盖了配置文件

**解决方法**:
```bash
# 1. 检查文件路径
ls -la backend/config/settings.yaml

# 2. 验证 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('backend/config/settings.yaml'))"

# 3. 检查是否有环境变量覆盖
env | grep AEROTRI

# 4. 查看启动日志中的配置加载信息
# 应该看到:
# INFO: Loaded config from: .../backend/config/settings.yaml
```

### 问题2: 数据库路径错误

**症状**: 系统创建了新的空数据库，历史数据丢失

**解决方法**:
```yaml
# 在 backend/config/settings.yaml 中明确指定旧数据库路径
database:
  path: "/path/to/your/old/aerotri.db"  # 使用绝对路径
```

或使用环境变量：
```bash
export AEROTRI_DB_PATH=/path/to/your/old/aerotri.db
```

### 问题3: 相对路径解析错误

**症状**: 相对路径被解析到错误的位置

**理解路径解析**:
- 配置文件位置: `backend/config/settings.yaml`
- 代码位置: `backend/app/conf/settings.py`
- 检测的项目根目录: `backend/`

**路径解析示例**:
```yaml
# 假设项目路径: /root/work/Aerotri-Web/aerotri-web/backend

paths:
  data_dir: "./data"          # 解析为: /root/work/Aerotri-Web/aerotri-web/backend/data
  data_dir: "../shared"       # 解析为: /root/work/Aerotri-Web/aerotri-web/shared
  data_dir: "/var/lib/data"   # 解析为: /var/lib/data (绝对路径不变)
```

### 问题4: 算法路径找不到

**症状**: 启动日志显示算法可执行文件缺失

**解决方法**:
```bash
# 1. 检查算法是否在 PATH 中
which colmap

# 2. 如果不在 PATH，使用绝对路径
export COLMAP_PATH=/usr/local/bin/colmap

# 3. 或在配置文件中使用绝对路径
# 编辑 backend/config/settings.yaml:
algorithms:
  colmap:
    path: "/usr/local/bin/colmap"
```

---

## 配置验证

### 自动验证

启动时会自动验证：
- ✅ 数据库路径可写
- ✅ 输出目录可创建
- ✅ 至少一个图像根路径有效
- ⚠️ 算法可执行文件存在（警告不阻塞）

### 手动验证

```python
from app.conf.validation import validate_on_startup

warnings = validate_on_startup()
for warning in warnings:
    print(f"Warning: {warning}")
```

---

## 相关文档

- [MIGRATION.md](MIGRATION.md) - 从旧配置迁移指南
- [ALGORITHM_INPUT_OUTPUT_ANALYSIS.md](../ALGORITHM_INPUT_OUTPUT_ANALYSIS.md) - 算法输入输出目录分析
- [README.md](../README.md) - 项目总览

---

## 获取帮助

如有问题或建议，请：
1. 查阅本文档的常见问题部分
2. 查看 GitHub Issues
3. 提交新的 Issue 描述你的问题
