# Aerotri-Web 特性详解

本文档详细介绍 Aerotri-Web 的所有功能特性。

## 目录

- [核心特性](#核心特性)
- [智能诊断 Agent](#智能诊断-agent-diagnostic-agent)
- [通知服务](#通知服务-notification-services)
- [任务队列管理](#任务队列管理-task-queue)
- [模型对比](#模型对比)
- [其他特性](#其他特性)

---

## 核心特性

### 多算法支持

Aerotri-Web 集成了多种 SfM（Structure-from-Motion）算法，满足不同场景需求：

| 算法 | 类型 | 速度 | GPU需求 | 适用场景 |
|------|------|------|---------|----------|
| COLMAP | 增量式 | 中 | 推荐 | 常规摄影测量 |
| GLOMAP | 全局式 | 快 | 推荐 | 大规模航拍 |
| InstantSfM | 全局式 | 很快 | 必需 | 实时可视化 |
| OpenMVG | 全局式 | 中 | 否 | CPU环境 |

👉 **详细说明**: [算法文档](./04-algorithms/)

### 密集重建

OpenMVS 密集重建管道：

1. **Densify** - 密集点云生成
2. **Meshing** - 三角网格重建
3. **Refine** - 网格优化
4. **Texture** - 纹理映射

支持多版本管理，可创建多个重建版本进行效果对比。

### 3D Gaussian Splatting

高质量 3D 渲染：

- **实时渲染**: 高帧率 3D 场景展示
- **SPZ 压缩**: ~10x 压缩比，减少存储和传输
- **训练监控**: TensorBoard 可视化
- **自动配置**: 相机模型自动检测和转换

### 3D Tiles 转换

支持 OpenMVS 和 3DGS 输出转换为 3D Tiles：

- **格式转换**: OBJ/GLB → 3D Tiles 1.1
- **地理定位**: 自动注入 ENU→ECEF 变换矩阵
- **SPZ 支持**: 支持 `KHR_gaussian_splatting_compression_spz_2` 扩展
- **Cesium 兼容**: 完美支持 CesiumJS 查看器

### 地理参考

GPS 坐标转换：

```
EXIF GPS → WGS84 → UTM → ENU (局部坐标系)
```

- 自动提取 EXIF GPS 信息
- 支持外部参考图像文件
- 生成 `geo_ref.json` 包含完整转换信息
- 3D Tiles 自动应用地理变换

---

## 智能诊断 Agent (Diagnostic Agent)

基于 **OpenClaw** 的 AI 驱动任务诊断系统。

### 工作流程

```
任务失败 → 收集上下文 → OpenClaw 诊断 → 生成报告 → 可选自动修复
```

### 诊断能力

- **失败原因分析**: 基于日志和错误堆栈分析
- **代码定位**: 精确定位到具体代码位置
- **修复建议**: 提供详细的修复步骤
- **自动修复**: 可选自动执行修复（谨慎使用）

### 配置

文件: `aerotri-web/backend/config/observability.yaml`

```yaml
diagnostic:
  enabled: true  # 启用诊断
  openclaw_cmd: "openclaw"
  agent_id: "main"
  timeout_seconds: 180
```

### 诊断示例

**输入**: RuntimeError: CUDA out of memory

**输出**:
```
错误类型: GPU内存不足
根本原因: 数据集包含5000+高分辨率图像
修复建议:
1. 降低 max_num_features 到 8192
2. 使用分区模式处理
3. 更换到更大显存的GPU
```

👉 **详细配置**: [NOTIFICATION_SETUP.md - AI诊断](./NOTIFICATION_SETUP.md/#ai诊断agent通知)

---

## 通知服务

企业级通知服务，支持钉钉和飞书。

### 支持的事件

| 事件类型 | 说明 | 默认频率 |
|---------|------|----------|
| task_started | 任务开始 | 实时 |
| task_completed | 任务完成 | 实时 |
| task_failed | 任务失败 | 实时 |
| backend_startup | 后端启动 | 一次性 |
| backend_shutdown | 后端关闭 | 一次性 |
| system_status | 系统状态 | 周期性 |
| task_summary | 任务汇总 | 每日定时 |

### 多通道配置

支持配置多个群聊，每个群聊接收不同类型的通知：

```yaml
notification:
  dingtalk:
    channels:
      # 任务执行群
      block_events:
        enabled: true
        webhook_url: "..."
        events:
          - task_started
          - task_completed
      
      # 运维监控群
      ops_team:
        enabled: true
        webhook_url: "..."
        events:
          - backend_startup
          - system_status
```

👉 **详细配置**: [NOTIFICATION_SETUP.md](./NOTIFICATION_SETUP.md/)

---

## 任务队列管理

### 功能特性

- **自动调度**: 基于 `max_concurrent` 并发限制
- **队列管理**: 支持置顶、删除、查询
- **并发控制**: 可配置 1-10 并发任务
- **实时状态**: WebSocket 实时更新

### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/queue/blocks` | GET | 获取队列列表 |
| `/api/queue/blocks/{id}/enqueue` | POST | 添加到队列 |
| `/api/queue/blocks/{id}/dequeue` | POST | 从队列删除 |
| `/api/queue/blocks/{id}/move-to-top` | POST | 置顶任务 |
| `/api/queue/config` | GET/PUT | 获取/更新并发限制 |

### 环境变量

- `QUEUE_MAX_CONCURRENT`: 最大并发数（默认: 1，范围: 1-10）

---

## 模型对比

### Block 级别对比

**功能**: 对比不同 Block 的算法效果

**支持场景**:
- 不同空三算法对比
- 同一算法不同参数对比
- 不同数据集效果对比

**对比维度**:
- 稀疏重建统计（图像数、点云数、相机数）
- 重投影误差分布
- 相机参数对比

### 重建版本级别对比

#### Cesium 分屏对比 (SplitCesiumViewer)

- 双 Cesium Viewer 分屏显示
- 可选视角同步
- 可拖动分屏线
- 适用于不同重建版本的 3D Tiles 模型对比

#### 刷子式对比 (BrushCompareViewer)

- 单 Cesium Viewer + 后端 stencil 裁剪
- 高性能实现
- 拖动分屏线实时切换
- 适用于精细对比

### API 支持

- `GET /api/blocks/{id}/recon-versions` - 获取重建版本列表
- `POST /api/blocks/{id}/recon-versions` - 创建新版本
- `DELETE /api/blocks/{id}/recon-versions/{version_id}` - 删除版本

---

## 其他特性

### 分区处理

大数据集支持分区和合并：
- 自动分区
- 并行处理
- 智能合并
- ID 重映射

### GPU 监控

- 实时 GPU 状态监控
- 显存使用情况
- 智能 GPU 分配
- 多 GPU 支持

### 实时进度

- WebSocket 实时进度更新
- 日志实时输出
- 可取消任务
- 错误实时反馈

👉 **了解更多**: [用户指南](./03-user-guide/)
