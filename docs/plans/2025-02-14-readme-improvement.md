# README.md Documentation Improvement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update and improve the README.md documentation to accurately describe all features, add missing capabilities, and correct inaccuracies.

**Architecture:** A single comprehensive documentation update task that reviews existing content and adds/corrects sections for all identified missing features.

**Tech Stack:** Markdown documentation, referencing existing codebase files for accuracy.

---

## Task 1: Read and Analyze Current README.md

**Files:**
- Read: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`
- Reference: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/aerotri-web/backend/config/observability.yaml`
- Reference: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/aerotri-web/frontend/src/stores/queue.ts`
- Reference: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/aerotri-web/frontend/src/views/CompareView.vue`
- Reference: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/aerotri-web/frontend/src/components/BrushCompareViewer.vue`
- Reference: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/aerotri-web/frontend/src/components/SplitCesiumViewer.vue`
- Reference: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/aerotri-web/backend/app/services/openclaw_diagnostic_agent.py`

**Step 1: Identify all sections requiring updates**

Create a checklist of issues found:
- [ ] Docker section mentions `docker-compose up -d` but no docker-compose.yml exists at root
- [ ] SPZ compression is documented but could be enhanced with more details
- [ ] Notification services (DingTalk/Feishu) completely missing
- [ ] Intelligent diagnostic Agent (OpenClaw) not explained
- [ ] Task queue features (pin to top, delete) not mentioned
- [ ] Reconstruction version management and model comparison missing
- [ ] Block comparison features missing
- [ ] Cesium split-screen and brush comparison features missing
- [ ] Visionary viewer missing from algorithm libraries list
- [ ] Future development plans section missing

**Step 2: Verify backend requirements.txt exists**

Check: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/aerotri-web/backend/requirements.txt`
Expected: File exists and contains FastAPI, uvicorn, SQLAlchemy, etc.

**Step 3: Verify visionary directory exists**

Check: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/visionary`
Expected: Directory exists with visionary 3DGS viewer

---

## Task 2: Remove/Correct Inaccurate Docker Quick Start Section

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md` (lines 36-50)

**Step 1: Remove Docker Quick Start section**

The section starting at line 38 `### Docker 快速启动（推荐）` through line 50 should be removed or corrected since no `docker-compose.yml` exists at the repository root.

**Action:** Either:
1. Remove the entire Docker section if no Docker setup exists
2. Or change to note that Docker is available only for submodules (e.g., openMVS)

**Recommended change:** Replace with note about local development only, with optional reference to submodule Dockerfiles.

---

## Task 3: Update Features Section (✨ 特性)

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md` (lines 12-22)

**Step 1: Add SPZ compression to features list**

Add after line 16 `- **3D Gaussian Splatting**: 高质量 3D 渲染`:
```markdown
- **SPZ 压缩**: 3DGS 点云压缩 (~10x 压缩比)，支持 `KHR_gaussian_splatting_compression_spz_2` 扩展
```

**Step 2: Add notification services to features list**

Add after line 20 `- **智能诊断**: AI 驱动的任务失败诊断和自动修复`:
```markdown
- **企业通知**: 钉钉/飞书集成，支持任务状态监控、周期性汇总、系统健康上报
- **智能诊断**: 基于 OpenClaw 的 AI 驱动任务失败诊断和自动修复
```

**Step 3: Add queue management features**

Add to features list:
```markdown
- **任务队列**: 支持置顶、删除、并发控制 (1-10)、自动调度
```

**Step 4: Add version management and comparison features**

Add to features list:
```markdown
- **多版本管理**: 重建管线支持多版本参数管理和效果对比
- **模型对比**: Cesium 分屏同步对比、刷子式对比，支持 Block 级别和重建版本级别对比
```

---

## Task 4: Update Notification Services Documentation

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`

**Step 1: Add new section after "智能诊断 Agent"**

Add at approximately line 280 (after GPU monitoring section):
```markdown
## 🔔 通知服务 (Notification Services)

Aerotri-Web 集成企业级通知服务，支持钉钉和飞书：

### 钉钉集成

配置文件：`aerotri-web/backend/config/observability.yaml`

支持多通道通知：

| 通道 | 用途 | 事件类型 |
|------|------|----------|
| **block_events** | Block 运行通知 | task_started, task_completed, task_failed, diagnosis_completed |
| **backend_status** | 后端状态 | system_status, backend_startup, backend_shutdown, backend_error |
| **task_monitor** | 任务监控 | periodic_task_summary (周期性任务汇总) |

### 飞书集成

当前版本支持飞书配置框架（后续迭代）。

### 周期性汇总

- **任务汇总**: 每日定时发送 (cron 配置)
- **系统状态**: 周期性健康检查 (interval 配置)

### 配置示例

```yaml
notification:
  enabled: true
  dingtalk:
    channels:
      block_events:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
        secret: "YOUR_SECRET"
  periodic:
    task_summary:
      enabled: true
      cron: "0 21 * * *"  # 每天 21:00
```
```

---

## Task 5: Update Intelligent Diagnostic Agent Documentation

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`

**Step 1: Update "智能诊断" section**

Update the existing mention (line 20) to be more descriptive, and add a dedicated section:

```markdown
## 🤖 智能诊断 Agent (Diagnostic Agent)

基于 **OpenClaw** 的 AI 驱动任务诊断系统：

### 工作流程

1. **触发**: 任务失败时自动触发
2. **上下文收集**: 收集日志、系统状态、Block 信息、错误堆栈
3. **诊断分析**: 发送给 OpenClaw Agent 进行智能分析
4. **结果输出**: 生成诊断报告并可选自动修复

### 配置

文件：`aerotri-web/backend/config/observability.yaml`

```yaml
diagnostic:
  enabled: true
  openclaw_cmd: "openclaw"
  agent_id: "main"
  agent_memory_path: "/path/to/AerotriWeb_AGENT.md"
  claude_md_path: "/path/to/CLAUDE.md"
  timeout_seconds: 180
  auto_fix: false  # 谨慎启用自动修复
```

### OpenClaw Agent 知识库

Agent 使用项目文档 (`CLAUDE.md`) 和历史诊断经验作为知识库，提供：
- 失败原因分析
- 代码位置定位
- 修复建议
- 自动修复（可选）
```

---

## Task 6: Add Task Queue Management Documentation

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`

**Step 1: Add new section**

Add after Intelligent Diagnostic Agent section:
```markdown
## 📋 任务队列管理 (Task Queue)

### 功能特性

- **自动调度**: 基于 `max_concurrent` 并发限制自动分发任务
- **队列管理**: 支持置顶 (moveToTop)、删除 (dequeue)、查询 (enqueue)
- **并发控制**: 可配置 1-10 并发任务数
- **实时状态**: WebSocket 实时更新队列状态和运行任务数

### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/queue/blocks` | GET | 获取队列列表 |
| `/api/queue/blocks/{id}/enqueue` | POST | 添加到队列 |
| `/api/queue/blocks/{id}/dequeue` | POST | 从队列删除 |
| `/api/queue/blocks/{id}/move-to-top` | POST | 置顶任务 |
| `/api/queue/config` | GET | 获取队列配置 |
| `/api/queue/config` | PUT | 更新并发限制 |

### 环境变量

- `QUEUE_MAX_CONCURRENT`: 最大并发任务数 (默认: 1, 范围: 1-10)
```

---

## Task 7: Add Model Comparison Documentation

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`

**Step 1: Add new section**

Add after Task Queue section:
```markdown
## 🔍 模型对比 (Model Comparison)

### 多版本管理

支持为每个 Block 创建多个重建版本 (ReconVersion)，每个版本独立管理：
- 独立的 OpenMVS 重建参数 (密集重建、网格、纹理)
- 独立的输出目录 (dense/, mesh/, refine/, texture/)
- 独立的 3D Tiles 转换状态
- 版本间参数和效果对比

### Block 级别对比

**功能**: 对比不同 Block 的算法效果

**支持场景**:
- 不同空三算法对比 (COLMAP vs GLOMAP vs InstantSfM vs OpenMVG)
- 同一算法不同参数对比
- 不同数据集效果对比

**页面**: `CompareView.vue`

**对比维度**:
- 稀疏重建统计 (图像数、点云数、相机数)
- 重投影误差分布
- 相机参数对比

### 重建版本级别对比

#### Cesium 分屏对比 (SplitCesiumViewer)

**位置**: 3D Tiles Tab

**特性**:
- 双 Cesium Viewer 分屏显示
- **视角同步**: 可选开启/关闭相机同步
- 可拖动分屏线调整左右比例
- 支持不同重建版本的 3D Tiles 模型对比

#### 刷子式对比 (BrushCompareViewer)

**位置**: 重建 Tab → "对比模型" 按钮

**特性**:
- **单 Cesium Viewer + 后端 stencil 裁剪**: 高性能实现
- 拖动分屏线实时切换左右模型显示
- 刷子式交互：左侧显示左模型，右侧显示右模型
- 适用于同一场景不同参数的精细对比

### API 支持

- `GET /api/blocks/{id}/recon-versions` - 获取重建版本列表
- `POST /api/blocks/{id}/recon-versions` - 创建新版本
- `GET /api/blocks/{id}/recon-versions/{version_id}` - 获取版本详情
- `DELETE /api/blocks/{id}/recon-versions/{version_id}` - 删除版本
- `POST /api/blocks/{id}/recon-versions/{version_id}/cancel` - 取消运行中版本
```

---

## Task 8: Update Algorithm Libraries Table

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md` (lines 132-141)

**Step 1: Add Visionary to the table**

Add after line 140:
```markdown
| **Visionary** | 3DGS 查看 | [源码](https://github.com/Visionary-Laboratory/visionary) | MIT |
```

Also update the summary text to mention Visionary as the recommended WebGPU 3DGS viewer.

---

## Task 9: Add Demo Videos Section

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`

**Step 1: Evaluate and add video links**

Add after AI Collaboration Highlights section (after line 34):

```markdown
## 🎬 演示视频

观看产品演示了解功能：

- [完整功能演示](https://www.bilibili.com/video/BV17EzQBzEP3/) - 核心功能完整演示
- [模型对比功能演示](https://www.bilibili.com/video/BV1mS6uB3Eyu/) - Block 对比和重建版本对比
```

---

## Task 10: Fix Backend Dependencies Section

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md` (lines 54-59)

**Step 1: Update backend installation section**

Replace the current backend section:
```markdown
**后端**:
```bash
cd aerotri-web/backend
# 安装依赖
pip install -r requirements.txt
# 或手动安装核心依赖
pip install fastapi uvicorn sqlalchemy pydantic aiofiles python-multipart
# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
```

---

## Task 11: Update Configuration Documentation

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md` (lines 348-359)

**Step 1: Correct configuration file path**

Update line 351:
```markdown
- **[配置指南](aerotri-web/backend/config/CONFIGURATION_GUIDE.md)** - 所有配置参数说明
- **[可观测性配置](aerotri-web/backend/config/observability.yaml.example)** - 通知和诊断配置
```

**Step 2: Update quick configuration section**

Update lines 353-358:
```markdown
快速配置：
```bash
cd aerotri-web/backend/config
cp settings.yaml.example settings.yaml
cp observability.yaml.example observability.yaml  # 可选
vim settings.yaml  # 编辑你的配置
```
```

---

## Task 12: Add Future Development Roadmap

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md` (update lines 315-321)

**Step 1: Update roadmap section**

Replace current roadmap:
```markdown
## 🗺️ 后续开发规划

### 短期 (3-6 个月)
- [ ] 大场景分 Tile 重建支持
- [ ] ROI (感兴趣区域) 设置和选择性重建
- [ ] 大场景 3DGS 分 chunk 训练
- [ ] 3DGS 多 GPU 并行训练

### 中期 (6-12 个月)
- [ ] 手持激光雷达工作流集成
- [ ] 更多 3D Tiles 扩展支持
- [ ] 云端部署方案

### 开源路线图
- [x] Phase 1: 基础设施（文档目录、GitHub 模板）
- [x] Phase 2: AI 协作专区（Case Studies）
- [x] Phase 3: OpenClaw 集成（智能诊断）
- [ ] Phase 4: 示例与教程
- [ ] Phase 5: 社区运营
```

---

## Task 13: Review and Final Polish

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`

**Step 1: Cross-reference validation**

Verify all sections:
- [ ] All file paths are correct
- [ ] All feature descriptions match actual implementation
- [ ] All code examples are accurate
- [ ] Links point to correct locations
- [ ] Chinese text is natural and consistent
- [ ] Badge URLs are correct

**Step 2: Add table of contents (optional)**

Consider adding a TOC at the top for long documentation.

**Step 3: Test all links**

Verify all internal and external links work:
- Documentation links (`./docs/...`)
- GitHub links in algorithm tables
- Video links (Bilibili)

**Step 4: Final review**

Read through entire README to ensure:
- Flow is logical
- No duplicate information
- All sections are complete
- Tone is appropriate for open-source project

---

## Task 14: Commit Changes

**Files:**
- Modify: `/Users/yangchengshuai/Documents/Github/Aerotri-Web/README.md`

**Step 1: Create git commit**

```bash
cd /Users/yangchengshuai/Documents/Github/Aerotri-Web
git add README.md
git commit -m "docs: 完善 README.md 文档

- 新增 SPZ 压缩支持说明
- 新增钉钉/飞书通知服务文档
- 新增 OpenClaw 智能诊断 Agent 文档
- 新增任务队列管理功能说明
- 新增多版本管理和模型对比文档
- 新增 Cesium 分屏和刷子式对比说明
- 更新算法库列表添加 Visionary
- 更新配置文档路径说明
- 移除不准确的 Docker 快速启动说明
- 新增演示视频链接
- 新增后续开发规划

详细更新内容见各 Task 说明"
```

**Step 2: Verify commit**

```bash
git log -1 --stat
```

Expected: README.md modified with comprehensive documentation updates
