# AeroTri-Web 配置指南

本文档提供 AeroTri-Web 后端的完整配置说明，帮助用户快速了解和设置所有参数。

---

## 📁 配置文件结构

```
aerotri-web/backend/config/
├── defaults.yaml           # 默认配置（版本控制）
├── settings.yaml           # 用户自定义配置（可选，git 忽略）
├── image_roots.yaml       # 图片根路径配置（可选）
└── notification.yaml        # 钉钉通知配置（可选）
```

**配置优先级**（从高到低）:
1. 环境变量
2. `config/settings.yaml` - 用户自定义
3. `config/defaults.yaml` - 默认值

---

## ⚙️ 快速配置向导

### 第一步：复制配置模板

```bash
cd /root/work/Aerotri-Web/aerotri-web/backend/config

# 创建用户配置文件（可选）
cp settings.yaml.example settings.yaml

# 创建图片路径配置（可选）
cp image_roots.yaml.example image_roots.yaml

# 创建通知配置（可选）
cp notification.yaml.example notification.yaml
```

### 第二步：编辑配置文件

```bash
# 使用你喜欢的编辑器
vim settings.yaml
```

### 第三步：重启后端

```bash
# 配置修改后重启后端生效
systemctl restart aerotri-backend  # 或
uvicorn app.main:app --reload
```

---

## 📋 完整配置参数说明

### 1. 基础配置 (`app`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `name` | string | `"AeroTri-Web"` | 应用名称 |
| `version` | string | `"1.0.0"` | 版本号 |
| `debug` | boolean | `false` | 调试模式 |
| `environment` | string | `"production"` | 运行环境 |
| `cors_origins` | list | `["http://localhost:5173"]` | CORS 允许的源 |
| `log_level` | string | `"INFO"` | 日志级别 |

---

### 2. 路径配置 (`paths`)

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `project_root` | string | `".."` | 项目根目录（相对路径基于 `config/` 目录） |
| `data_dir` | string | `"./data"` | 数据目录 |
| `outputs_dir` | string | `"./data/outputs"` | 任务输出目录 |
| `blocks_dir` | string | `"./data/blocks"` | Block 数据目录 |
| `thumbnails_dir` | string | `"./data/thumbnails"` | 缩略图目录 |

**路径说明**:
- 所有相对路径都相对于 `backend/config/` 目录解析
- 推荐使用绝对路径避免混淆
- 示例：`/root/work/aerotri-web/data`

---

### 3. 数据库配置 (`database`)

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `path` | string | `"./data/aerotri.db"` | `AEROTRI_DB_PATH` | SQLite 数据库文件路径 |
| `pool_size` | integer | `5` | 连接池大小 |
| `max_overflow` | integer | `10` | 最大溢出连接数 |

---

### 4. 算法路径配置 (`algorithms`)

#### COLMAP

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `path` | string | `"colmap"` | `COLMAP_PATH` | COLMAP 可执行文件路径 |

#### GLOMAP

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `path` | string | `"glomap"` | `GLOMAP_PATH` | GLOMAP 可执行文件路径 |

#### InstantSfM

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `path` | string | `"ins-sfm"` | `INSTANTSFM_PATH` | InstantSfM 可执行文件路径 |

#### OpenMVG

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `bin_dir` | string | `/usr/local/bin` | `OPENMVG_BIN_DIR` | OpenMVG 二进制文件目录 |
| `sensor_db` | string | `/usr/local/share/...` | `OPENMVG_SENSOR_DB` | 相机传感器数据库路径 |

#### OpenMVS

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `bin_dir` | string | `/usr/local/lib/...` | - | OpenMVS 二进制文件目录 |

---

### 5. 3D Gaussian Splatting 配置 (`gaussian_splatting`)

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `repo_path` | string | `"./gs_workspace/..."` | `GS_REPO_PATH` | 3DGS 仓库路径（包含 `train.py`） |
| `python` | string | `"python"` | `GS_PYTHON` | Python 解释器路径（用于 3DGS） |
| `tensorboard_path` | string | `"tensorboard"` | TensorBoard 可执行文件 |
| `tensorboard_port_start` | integer | `6006` | TensorBoard 端口起始值 |
| `network_gui_ip` | string | `"127.0.0.1"` | Network GUI 监听 IP |
| `network_gui_port_start` | integer | `6009` | Network GUI 端口起始值 |

---

### 6. 队列配置 (`queue`)

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `max_concurrent` | integer | `1` | `QUEUE_MAX_CONCURRENT` | 最大并发任务数（1-10） |
| `scheduler_interval` | integer | `5` | 调度器轮询间隔（秒） |

**重要**: `max_concurrent` 控制同时运行的任务数量，建议根据 GPU 内存调整：
- 24GB 显存：1-2 个任务
- 48GB+ 显存：2-4 个任务

---

### 7. GPU 配置 (`gpu`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|---------|------|
| `monitor_interval` | integer | `2` | GPU 监控轮询间隔（秒） |
| `auto_selection` | string | `"most_free"` | 自动 GPU 选择策略 |
| `default_device` | integer | `0` | 默认 GPU 设备 ID |

**GPU 选择策略**:
- `most_free`: 选择显存最多的 GPU
- `least_used`: 选择显存使用最少的 GPU
- 具体设备 ID: 强制使用指定 GPU

---

### 8. 图片根路径配置 (`image_roots`)

支持单个或多个图片根目录配置：

#### 单个路径（向后兼容）

```bash
# 环境变量
export AEROTRI_IMAGE_ROOT="/data/images"

# 或在 image_roots.yaml 中
default: "/data/images"
```

#### 多个路径（推荐）

```yaml
# image_roots.yaml
paths:
  - name: "本地数据"
    path: "/data/images"
  - name: "NAS 存储"
    path: "/mnt/nas/images"
  - name: "外部硬盘"
    path: "/mnt/usb/images"
```

```bash
# 环境变量（冒号分隔）
export AEROTRI_IMAGE_ROOTS="/data/images:/mnt/nas/images:/mnt/usb/images"
```

**配置优先级**:
1. `AEROTRI_IMAGE_ROOTS`（多个）
2. `AEROTRI_IMAGE_ROOT`（单个）
3. `image_roots.yaml` 文件
4. 默认值 `/mnt/work_odm/chengshuai`

---

### 9. 通知配置 (`notification`)

#### 9.1 启用/禁用

```yaml
notification:
  enabled: true  # 全局开关
```

#### 9.2 钉钉通知

```yaml
notification:
  block_events:
    enabled: true
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=..."
    secret: "SECxxxxx"  # 签名密钥（可选）
    events:
      - task_started      # 任务开始
      - task_completed    # 任务完成
      - task_failed       # 任务失败
      - diagnosis_completed  # AI 诊断完成
```

**获取 Webhook 和 Secret**:
1. 登录 [钉钉开放平台](https://open.dingtalk.com/)
2. 创建群机器人
3. 获取 `webhook_url` 和 `secret`
4. 配置到 `notification.yaml`

---

### 10. 诊断 Agent 配置 (`diagnostic`)

#### 10.1 基础配置

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `enabled` | boolean | `false` | - | 诊断功能全局开关（默认关闭） |
| `openclaw_cmd` | string | `"openclaw"` | - | OpenClaw CLI 命令 |
| `agent_id` | string | `"main"` | - | OpenClaw Agent ID |
| `timeout_seconds` | integer | `180` | - | OpenClaw 调用超时时间（秒） |
| `auto_fix` | boolean | `false` | - | 是否尝试自动修复（谨慎启用） |

#### 10.2 路径配置

| 参数 | 类型 | 默认值 | 环境变量 | 说明 |
|------|------|---------|-------------|------|
| `agent_memory_path` | Path | `"./data/diagnostics/..."` | `AEROTRI_DIAGNOSTIC_AGENT_MEMORY` | Agent 知识库（经验积累） |
| `history_log_path` | Path | `"./data/diagnostics/..."` | `AEROTRI_DIAGNOSTIC_HISTORY_LOG` | 诊断历史记录 |
| `claude_md_path` | Path | `"./CLAUDE.md"` | `AEROTRI_DIAGNOSTIC_CLAUDE_MD` | 项目文档路径 |
| `context_output_dir` | Path | `"./data/diagnostics/contexts"` | `AEROTRI_DIAGNOSTIC_CONTEXT_DIR` | 调试上下文输出目录 |

**路径说明**:
- 支持绝对路径和相对路径
- 绝对路径：直接使用，推荐方式
- 相对路径：相对于 `backend/config/` 解析
- `agent_memory_path` 需要手动创建（可使用提供的模板）
- 其他文件代码会自动创建

#### 10.3 诊断功能工作流程

```
任务失败 → 收集上下文 → 调用 OpenClaw → 解析结果 → 发送钉钉通知
                                    ↓
                            保存上下文到文件（调试）
                            保存诊断历史（知识积累）
```

#### 10.4 启用诊断功能

```yaml
# config/settings.yaml 或 config/defaults.yaml
diagnostic:
  enabled: true  # 设置为 true 启用
  openclaw_cmd: "openclaw"
  agent_id: "main"
```

**前提条件**:
1. OpenClaw CLI 已安装并在 PATH 中
2. 配置了有效的 Agent ID（`main` 或自定义）
3. `agent_memory_path` 文件存在（可选，代码会处理不存在情况）

#### 10.5 通知配置

```yaml
notification:
  block_events:
    events:
      - task_failed         # 立即失败通知
      - diagnosis_completed  # AI 诊断完成通知
```

---

## 🔧 环境变量完整列表

### 路径相关

```bash
# 项目路径
export AEROTRI_DB_PATH="/custom/path/to/aerotri.db"

# 图片根路径
export AEROTRI_IMAGE_ROOT="/data/images"
export AEROTRI_IMAGE_ROOTS="/data/images:/mnt/nas/images"

# 算法路径
export COLMAP_PATH="/usr/local/bin/colmap"
export GLOMAP_PATH="/usr/local/bin/glomap"
export INSTANTSFM_PATH="/usr/local/bin/ins-sfm"
export OPENMVG_BIN_DIR="/usr/local/bin/openmvg"
export OPENMVG_SENSOR_DB="/usr/local/share/sensor_width_camera_database.txt"

# 3DGS
export GS_REPO_PATH="/path/to/gaussian-splatting"
export GS_PYTHON="/path/to/python"

# SPZ 压缩
export SPZ_PYTHON="/path/to/spz-python"
```

### 功能相关

```bash
# 队列
export QUEUE_MAX_CONCURRENT=2

# cuDSS 加速
export CUDSS_DIR="/opt/cudss"

# 诊断 Agent
export AEROTRI_DIAGNOSTIC_AGENT_MEMORY="/path/to/AerotriWeb_AGENT.md"
export AEROTRI_DIAGNOSTIC_HISTORY_LOG="/path/to/diagnosis_history.log"
export AEROTRI_DIAGNOSTIC_CLAUDE_MD="/path/to/CLAUDE.md"
export AEROTRI_DIAGNOSTIC_CONTEXT_DIR="/path/to/contexts"
```

---

## 📊 配置场景示例

### 场景 1: 开发环境（最小配置）

```yaml
# config/settings.yaml
debug: true
log_level: "DEBUG"
diagnostic:
  enabled: false  # 开发时关闭诊断
```

### 场景 2: 生产环境（多 GPU）

```yaml
# config/settings.yaml
queue:
  max_concurrent: 4  # 4 个 GPU 并发
gpu:
  auto_selection: "most_free"
diagnostic:
  enabled: true
  timeout_seconds: 300  # 复杂问题需要更多时间
```

### 场景 3: 开源发布（默认配置）

```yaml
# 使用 defaults.yaml 即可
# 或创建最小 settings.yaml:
database:
  path: "/var/lib/aerotri/aerotri.db"
image_roots:
  default: "/data/images"
diagnostic:
  enabled: false  # 默认关闭
```

---

## ✅ 配置验证

### 检查配置加载

```bash
cd /root/work/Aerotri-Web/aerotri-web/backend

# Python 检查
python3 -c "
from app.conf.settings import get_settings
settings = get_settings()
print('Database:', settings.database.path)
print('Diagnostic enabled:', settings.diagnostic.enabled)
"
```

### 检查路径存在性

```bash
# 数据库
ls -la /root/work/aerotri-web/data/aerotri.db

# 图片根目录
ls -la /data/images  # 或你配置的路径

# 诊断文件
ls -la /root/work/aerotri-web/data/diagnostics/
```

### 检查算法可执行性

```bash
# COLMAP
which colmap
colmap --help

# GLOMAP
which glomap

# OpenClaw
which openclaw
openclaw agent --help
```

---

## 🐛 常见问题

### Q1: 修改配置后不生效？

**A**: 重启后端服务
```bash
# 开发环境（自动重载）
uvicorn app.main:app --reload

# 生产环境
systemctl restart aerotri-backend
```

### Q2: 相对路径解析错误？

**A**: 使用绝对路径
```yaml
# 推荐
paths:
  data_dir: "/root/work/aerotri-web/data"

# 避免
paths:
  data_dir: "../../../data"  # 容易出错
```

### Q3: 诊断功能不工作？

**检查清单**:
1. ✅ `diagnostic.enabled: true`
2. ✅ OpenClaw 已安装：`which openclaw`
3. ✅ Agent ID 正确：`openclaw agent list`
4. ✅ 查看后端日志：`[DIAGNOSTIC]` 开头的信息

### Q4: 通知不发送？

**检查清单**:
1. ✅ `notification.enabled: true`
2. ✅ Webhook URL 正确（从钉钉获取）
3. ✅ Secret 正确（如果启用了签名）
4. ✅ 事件配置正确：`diagnosis_completed` 在 `events` 列表中

---

## 📚 更多文档

- **算法配置**: 参见各算法官方文档
- **API 文档**: 启动后端访问 http://localhost:8000/docs
- **数据库模型**: `backend/app/models/`
- **开发指南**: `CLAUDE.md`

---

**最后更新**: 2026-02-11
**版本**: 1.0.0
