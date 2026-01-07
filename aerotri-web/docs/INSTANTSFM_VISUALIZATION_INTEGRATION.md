# InstantSfM 可视化工具集成开发方案

## 项目背景

将 InstantSfM 的实时可视化功能集成到 aerotri-web 平台中，当用户选择使用 InstantSfM 进行空三处理时，提供实时显示优化过程、相机位姿和点云的功能。

## 多角色讨论

### 1. 产品经理视角

#### 用户需求
- **核心需求**：在空三处理过程中实时查看优化进度
- **用户场景**：
  - 用户提交空三任务后，希望看到实时的优化过程
  - 了解相机位姿如何逐步优化
  - 观察点云如何逐步生成和优化
- **价值**：
  - 提升用户体验，减少等待焦虑
  - 帮助用户理解空三处理过程
  - 便于及时发现和处理问题

#### 功能定位
- **与现有 3D 查看器的关系**：
  - **3D 查看器（ThreeViewer）**：查看**最终结果**（静态）
  - **实时可视化**：查看**处理过程**（动态）
  - 两者互补，不是替代关系

#### 功能设计
1. **触发条件**：
   - 用户选择 InstantSfM 算法
   - 任务开始运行时自动启动可视化
   - 用户可选择是否启用（性能考虑）

2. **显示内容**：
   - 实时点云（逐步增加的点）
   - 相机位姿（逐步优化的相机位置和方向）
   - 优化阶段标识（当前处于哪个阶段）

3. **交互功能**：
   - 3D 场景旋转、缩放、平移
   - 点云大小调整
   - 相机视锥体显示/隐藏
   - 播放控制（如果支持回放）

### 2. 高级前端工程师视角

#### 技术架构

**方案 A：WebSocket + Three.js（推荐）**

```
┌─────────────────┐
│  InstantSfM     │
│  (--enable_gui) │
│  viser server   │
└────────┬────────┘
         │ WebSocket/HTTP
         │ (实时数据流)
         ▼
┌─────────────────┐
│  Backend Proxy   │
│  (WebSocket)     │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│  Frontend        │
│  Three.js        │
│  实时渲染        │
└─────────────────┘
```

**技术选型**：
- **实时通信**：WebSocket（复用现有架构）
- **3D 渲染**：Three.js（与现有 ThreeViewer 一致）
- **数据格式**：JSON（点云、相机位姿）

**实现要点**：
1. **数据流处理**：
   - 后端从 viser 服务器获取数据
   - 通过 WebSocket 推送到前端
   - 前端增量更新 Three.js 场景

2. **性能优化**：
   - 点云采样（显示部分点，避免卡顿）
   - 节流更新（限制更新频率）
   - 使用 BufferGeometry 高效渲染

3. **组件设计**：
   ```vue
   <InstantSfMRealtimeViewer
     :block-id="blockId"
     :enabled="isInstantsfm && taskRunning"
   />
   ```

**方案 B：iframe 嵌入 viser（简单但受限）**

- 直接嵌入 viser 的 Web 界面
- 优点：实现简单，功能完整
- 缺点：样式不一致，难以定制

#### 与现有组件的关系

```
BlockDetailView
├── ProgressView (任务进度)
├── ReconstructionPanel
│   ├── ThreeViewer (最终结果查看) ← 静态查看
│   └── InstantSfMRealtimeViewer (实时可视化) ← 新增，动态查看
└── StatisticsView
```

**集成位置**：
- 在 `BlockDetailView` 中添加新的 Tab 或 Panel
- 当任务运行且算法为 InstantSfM 时显示
- 任务完成后，可以切换到 ThreeViewer 查看最终结果

#### 前端实现细节

1. **组件结构**：
   ```typescript
   // components/InstantSfMRealtimeViewer.vue
   - 复用 ThreeViewer 的 Three.js 初始化逻辑
   - 添加 WebSocket 连接管理
   - 实现增量数据更新
   - 添加播放控制（如果支持回放）
   ```

2. **数据模型**：
   ```typescript
   interface RealtimeUpdate {
     step: number;
     stepName: string;
     cameras: CameraInfo[];
     points: Point3D[];
     timestamp: number;
   }
   ```

3. **状态管理**：
   - 使用现有的 WebSocket composable
   - 扩展 blocks store 以支持实时可视化状态

### 3. 高级后端处理工程师视角

#### 架构设计

**方案 A：代理模式（推荐）**

```
InstantSfM Process
  └─> viser server (localhost:随机端口)
         │
         ▼
Backend Proxy Service
  └─> WebSocket Server
         │
         ▼
Frontend Client
```

**实现要点**：

1. **viser 服务器管理**：
   - InstantSfM 启动时，viser 会在随机端口启动 HTTP/WebSocket 服务器
   - 后端需要捕获这个端口号
   - 管理 viser 服务器的生命周期

2. **数据转发**：
   ```python
   # app/services/instantsfm_visualizer_proxy.py
   class InstantSfMVisualizerProxy:
       def __init__(self, viser_port: int):
           self.viser_port = viser_port
           self.ws_clients = []
       
       async def forward_to_clients(self, data):
           # 从 viser 获取数据，转发给前端客户端
           pass
   ```

3. **集成到任务运行器**：
   ```python
   # task_runner.py
   async def _run_instantsfm_mapper(..., enable_visualization: bool = False):
       if enable_visualization:
           # 启动 viser（通过 --enable_gui）
           # 捕获 viser 端口
           # 启动代理服务
           pass
   ```

**方案 B：直接集成 viser 客户端**

- 后端直接使用 viser 的 Python API
- 从 `ReconstructionVisualizer` 获取数据
- 通过 WebSocket 推送到前端

#### 技术挑战

1. **端口管理**：
   - viser 使用随机端口
   - 需要从日志或环境变量中获取
   - 或修改 InstantSfM 代码以指定端口

2. **数据格式转换**：
   - viser 使用自己的数据格式
   - 需要转换为前端 Three.js 兼容格式

3. **生命周期管理**：
   - 任务开始时启动可视化
   - 任务结束时清理资源
   - 任务失败时也要清理

#### 实现细节

1. **修改任务运行器**：
   ```python
   # 在 _run_instantsfm_mapper 中
   if params.get("enable_visualization", False):
       # 添加 --enable_gui 参数
       base_cmd_parts[-1] += " --enable_gui"
       
       # 启动可视化代理
       visualizer_proxy = await self._start_visualizer_proxy(block_id)
   ```

2. **WebSocket 端点**：
   ```python
   # app/api/websocket.py (新增或扩展)
   @router.websocket("/ws/visualization/{block_id}")
   async def visualization_websocket(websocket: WebSocket, block_id: str):
       # 连接到 viser 服务器
       # 转发数据到前端
       pass
   ```

3. **数据流处理**：
   - 从 viser 的 HTTP API 获取场景数据
   - 或通过 WebSocket 订阅 viser 的更新
   - 转换为标准格式后推送到前端

### 4. 软件架构师视角

#### 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                       │
├─────────────────────────────────────────────────────────┤
│  BlockDetailView                                         │
│  ├── ThreeViewer (静态结果)                             │
│  └── InstantSfMRealtimeViewer (实时可视化) ← 新增        │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket
┌────────────────────▼────────────────────────────────────┐
│                  Backend Layer                           │
├─────────────────────────────────────────────────────────┤
│  TaskRunner                                             │
│  ├── _run_instantsfm_mapper                             │
│  │   └── InstantSfM Process (--enable_gui)             │
│  │       └── viser Server (随机端口)                    │
│  └── InstantSfMVisualizerProxy ← 新增                   │
│      └── WebSocket Server                                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              InstantSfM Process                          │
│  └── ReconstructionVisualizer (viser)                   │
└──────────────────────────────────────────────────────────┘
```

#### 设计原则

1. **解耦**：
   - 可视化功能与核心处理逻辑分离
   - 通过配置开关控制是否启用

2. **可扩展性**：
   - 支持未来其他算法的可视化
   - 统一的实时可视化接口

3. **性能**：
   - 可视化不应影响处理性能
   - 使用异步处理和消息队列

4. **容错性**：
   - 可视化失败不应影响主流程
   - 优雅降级（可视化不可用时显示静态进度）

#### 数据流设计

```
InstantSfM Process
  │
  ├─> ReconstructionVisualizer.add_step()
  │   └─> viser Server (更新场景)
  │
  └─> TaskRunner (日志解析)
      └─> WebSocket (进度更新)

Backend Proxy
  │
  ├─> 从 viser HTTP API 获取场景数据
  │   └─> 转换为标准格式
  │       └─> WebSocket 推送到前端
  │
  └─> 或直接订阅 viser WebSocket
      └─> 转发到前端
```

#### 接口设计

**后端 API**：
```python
# GET /api/blocks/{block_id}/visualization/status
# 返回可视化服务器状态和连接信息

# WebSocket /ws/visualization/{block_id}
# 实时推送可视化数据
```

**前端接口**：
```typescript
// composables/useInstantsfmVisualization.ts
export function useInstantsfmVisualization(blockId: string) {
  const connect = () => { /* 连接 WebSocket */ }
  const disconnect = () => { /* 断开连接 */ }
  const onUpdate = (callback: (data: RealtimeUpdate) => void) => { /* 监听更新 */ }
}
```

## 开发方案

### 阶段 1：基础集成（MVP）

**目标**：实现基本的实时可视化功能

**任务**：
1. ✅ 修复 InstantSfM 运行错误
2. 后端：添加可视化代理服务
3. 后端：修改任务运行器以支持 `--enable_gui`
4. 前端：创建 `InstantSfMRealtimeViewer` 组件
5. 前端：集成到 `BlockDetailView`

**时间估算**：3-5 天

### 阶段 2：功能完善

**目标**：添加交互功能和优化

**任务**：
1. 添加播放控制（如果支持回放）
2. 性能优化（点云采样、节流）
3. 错误处理和重连机制
4. UI/UX 优化

**时间估算**：2-3 天

### 阶段 3：高级功能

**目标**：添加高级可视化功能

**任务**：
1. 支持记录和回放
2. 多阶段对比（不同优化阶段对比）
3. 统计信息实时显示
4. 导出可视化视频

**时间估算**：3-5 天

## 技术决策

### 决策 1：数据获取方式

**选项 A**：从 viser HTTP API 获取（轮询）
- 优点：实现简单
- 缺点：延迟较高，资源消耗大

**选项 B**：订阅 viser WebSocket（推荐）
- 优点：实时性好，资源消耗低
- 缺点：需要处理 viser 的 WebSocket 协议

**决策**：选择选项 B，但提供选项 A 作为降级方案

### 决策 2：组件复用

**选项 A**：完全复用 ThreeViewer
- 优点：代码复用，维护简单
- 缺点：可能耦合度高

**选项 B**：创建独立组件，复用工具函数
- 优点：解耦，易于扩展
- 缺点：代码重复

**决策**：选择选项 B，提取公共工具函数到 `composables/useThreeScene.ts`

### 决策 3：可视化开关

**选项 A**：默认开启
- 优点：用户体验好
- 缺点：可能影响性能

**选项 B**：用户选择（推荐）
- 优点：灵活，不影响性能敏感用户
- 缺点：需要用户操作

**决策**：选择选项 B，在参数表单中添加"启用实时可视化"选项

## 实施计划

### 第一步：修复 InstantSfM 错误
- 执行错误修复方案
- 验证 InstantSfM 可以正常运行

### 第二步：后端开发
1. 创建 `InstantSfMVisualizerProxy` 服务
2. 修改 `TaskRunner` 以支持可视化
3. 添加 WebSocket 端点
4. 测试数据流

### 第三步：前端开发
1. 创建 `InstantSfMRealtimeViewer` 组件
2. 创建 `useInstantsfmVisualization` composable
3. 集成到 `BlockDetailView`
4. 测试实时更新

### 第四步：集成测试
1. 端到端测试
2. 性能测试
3. 错误处理测试

### 第五步：优化和文档
1. 性能优化
2. 代码审查
3. 文档编写

## 风险评估

1. **技术风险**：
   - viser 协议可能不公开或变化
   - 性能影响（实时渲染大量点云）
   - **缓解**：提供降级方案，性能监控

2. **集成风险**：
   - 与现有系统冲突
   - 数据格式不兼容
   - **缓解**：充分测试，版本控制

3. **维护风险**：
   - InstantSfM 更新可能破坏集成
   - **缓解**：版本锁定，持续关注上游更新

## 成功标准

1. ✅ 用户可以选择启用实时可视化
2. ✅ 实时显示点云和相机位姿
3. ✅ 不影响主处理流程性能
4. ✅ 错误处理完善，不会导致系统崩溃
5. ✅ UI/UX 与现有系统一致

## 后续优化

1. 支持其他算法的可视化
2. 添加更多交互功能
3. 性能进一步优化
4. 支持分布式可视化（多用户）

