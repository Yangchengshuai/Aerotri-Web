# 05-development

AeroTri-Web 开发指南，帮助开发者理解和扩展项目。

## 目录

- [系统架构](#系统架构)
- [后端开发](#后端开发)
- [前端开发](#前端开发)
- [API参考](#api参考)
- [WebSocket通信](#websocket通信)
- [测试](#测试)
- [部署](#部署)

---

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (Vue 3)              │
│  ┌─────────────┬─────────────┬───────────┐ │
│  │ HomeView    │ BlockDetail │ CompareView │ │
│  └─────────────┴─────────────┴───────────┘ │
│         ↓ HTTP + WebSocket                    │
└────────────────┬──────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│         Backend (FastAPI)                │
│  ┌──────────┬──────────┬───────────────┐│
│  │ task_    │ openmvs_ │ gs_         ││
│  │ runner    │ runner   │ runner      ││
│  └──────────┴──────────┴───────────────┘│
│         ↓                                   │
│  ┌────────────┬─────────────┬───────────────┐│
│  │ Algorithms │ External    │ Database      ││
│  │ (COLMAP,  │ Binaries   │ (SQLite)     ││
│  │ GLOMAP,    │            │              ││
│  │ InstantSfM)│            │              ││
│  └────────────┴─────────────┴───────────────┘│
└─────────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│              Data Storage                    │
│  ┌───────────┬───────────┬─────────────┐│
│  │ outputs/  │ blocks/   │ thumbnails/  ││
│  │           │           │             ││
│  └───────────┴───────────┴─────────────┘│
└─────────────────────────────────────────────────────┘
```

### 技术栈

**前端**：
- Vue 3.4+（组合式API）
- TypeScript 5.3+
- Pinia（状态管理）
- Element Plus（UI组件）
- Three.js / Cesium（3D可视化）

**后端**：
- FastAPI 0.100+
- SQLAlchemy 2.0（ORM）
- Pydantic 2.0（数据验证）
- uvicorn[standard]（ASGI服务器）
- aiofiles（异步文件操作）

---

## 后端开发

### 项目结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI应用入口
│   ├── config.py               # 配置加载器
│   ├── schemas.py              # Pydantic数据模型
│   │
│   ├── api/                    # RESTful API端点
│   │   ├── __init__.py
│   │   ├── blocks.py           # Block管理
│   │   ├── queue.py            # 任务队列
│   │   ├── reconstruction.py   # 密集重建（旧版）
│   │   ├── recon_versions.py   # 重建版本管理
│   │   ├── gs.py               # 3DGS训练
│   │   ├── gs_tiles.py         # 3DGS Tiles转换
│   │   ├── tiles.py            # OpenMVS Tiles转换
│   │   ├── filesystem.py       # 文件系统浏览
│   │   ├── georef.py           # 地理参考
│   │   ├── gpu.py              # GPU监控
│   │   ├── images.py           # 图像浏览
│   │   ├── partitions.py       # 分区管理
│   │   ├── results.py          # 结果读取
│   │   ├── tasks.py            # 任务管理
│   │   ├── unified_tasks.py    # 统一任务
│   │   └── system.py           # 系统管理
│   │   └── ...
│   │
│   ├── models/                 # SQLAlchemy ORM模型
│   │   ├── block.py
│   │   ├── partition.py
│   │   ├── recon_version.py
│   │   └── database.py
│   │
│   ├── services/              # 业务逻辑层
│   │   ├── task_runner.py        # SfM执行服务
│   │   ├── openmvs_runner.py     # OpenMVS密集重建
│   │   ├── gs_runner.py          # 3DGS训练
│   │   ├── tiles_runner.py       # 3D Tiles转换
│   │   ├── queue_scheduler.py     # 任务调度
│   │   ├── gpu_service.py        # GPU监控
│   │   ├── notification.py       # 通知服务
│   │   └── ...
│   │
│   └── ws/                    # WebSocket处理器
│       ├── progress.py          # 进度更新
│       └── visualization.py     # 实时可视化
│
├── tests/                     # 测试套件
│   ├── test_api.py
│   ├── test_services.py
│   └── ...
│
└── config/                    # 配置文件
    ├── application.yaml.example       # 应用配置模板
    ├── observability.yaml.example     # 可观测性配置模板
    └── ...
```

### 添加新API端点

1. **定义数据模型**（`app/schemas.py`）：
   ```python
   from pydantic import BaseModel, Field

   class MyRequest(BaseModel):
       name: str
       value: int = Field(..., ge=0, le=100)
   ```

2. **创建API路由**（`app/api/my_module.py`）：
   ```python
   from fastapi import APIRouter, Depends
   from ..schemas import MyRequest
   from ..models.database import get_db

   router = APIRouter(prefix="/api/my-module", tags=["My Module"])

   @router.post("/items", response_model=ItemResponse)
   async def create_item(
       request: MyRequest,
       db: AsyncSession = Depends(get_db)
   ):
       # 业务逻辑
       return {"id": "new-id"}
   ```

3. **注册路由**（`app/api/__init__.py`）：
   ```python
   from . import blocks, queue, system

   api_router = APIRouter()
   api_router.include_router(blocks.router)
   api_router.include_router(queue.router)
   api_router.include_router(system.router)
   ```

### 服务层模式

**单例服务**：
```python
# app/services/task_runner.py

class TaskRunner:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls._instance

    async def run_task(self, block_id: str):
        # 任务执行逻辑
        pass
```

**API层调用**：
```python
# app/api/blocks.py

from ..services.task_runner import task_runner

@router.post("/{block_id}/run")
async def run_block(block_id: str):
    runner = task_runner.get_instance()
    await runner.run_task(block_id)
```

### 数据库模型

**定义模型**（`app/models/block.py`）：
```python
from sqlalchemy import String, Integer, Enum, Boolean
from .database import Base

class Block(Base):
    __tablename__ = "blocks"

    id = mapped_column(String(36), primary_key=True)
    name = mapped_column(String(255), nullable=False)
    status = mapped_column(Enum(BlockStatus), default=BlockStatus.CREATED)

    def __repr__(self):
        return f"<Block(id={self.id}, name={self.name})>"
```

**使用模型**：
```python
# 查询
from sqlalchemy import select

async def get_block(db: AsyncSession, block_id: str):
    result = await db.execute(
        select(Block).where(Block.id == block_id)
    )
    return result.scalar_one()

# 创建
new_block = Block(
    id=str(uuid.uuid4()),
    name="My Block",
    status=BlockStatus.CREATED
)
db.add(new_block)
await db.commit()
```

---

## 前端开发

### 项目结构

```
frontend/
├── src/
│   ├── main.ts               # 应用入口
│   ├── router.ts            # 路由配置
│   │
│   ├── api/                 # API客户端
│   │   └── index.ts      # axios封装、类型定义
│   │
│   ├── stores/              # Pinia状态管理
│   │   ├── blocks.ts
│   │   ├── gpu.ts
│   │   └── queue.ts
│   │
│   ├── components/          # Vue组件
│   │   ├── BlockCard.vue
│   │   ├── ParameterForm.vue
│   │   └── ...
│   │
│   ├── views/              # 页面组件
│   │   ├── HomeView.vue
│   │   ├── BlockDetailView.vue
│   │   ├── CompareView.vue
│   │   ├── ReconCompareView.vue    # 重建版本对比
│   │   └── ...
│   │
│   ├── types/              # TypeScript类型
│   │   └── index.ts
│   │
│   └── composables/        # 组合式函数
│       └── ...
│
├── index.html               # HTML入口
├── vite.config.mjs         # Vite配置
├── tsconfig.json           # TypeScript配置
└── package.json            # 依赖管理
```

### 状态管理（Pinia）

**定义Store**：
```typescript
// src/stores/blocks.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useBlocksStore = defineStore('blocks', () => {
  // State
  blocks: ref<Block[]>([]),
  currentBlock: ref<Block | null>(null),
  loading: ref(false),

  // Getters
  blockCount: computed(() => blocks.value.length),

  // Actions
  async function fetchBlocks() {
    this.loading = true
    const response = await api.getBlocks()
    this.blocks = response.data
    this.loading = false
  },

  async function createBlock(data: BlockCreate) {
    const response = await api.createBlock(data)
    this.blocks.push(response.data)
  }
})
```

**使用Store**：
```vue
<script setup lang="ts">
import { useBlocksStore } from '@/stores/blocks'

const blocksStore = useBlocksStore()

onMounted(() => {
  blocksStore.fetchBlocks()
})
</script>

<template>
  <div v-for="block in blocksStore.blocks" :key="block.id">
    {{ block.name }}
  </div>
</template>
```

### 组件开发

**基础组件**：
```vue
<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  modelValue: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const internalValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})
</script>

<template>
  <input
    :value="internalValue"
    @input="emit('update:modelValue', $event.target.value)"
  />
</template>
```

### API客户端

**类型定义**：
```typescript
// src/api/index.ts
export interface Block {
  id: string
  name: string
  status: BlockStatus
  algorithm: AlgorithmType
}

export interface BlockCreate {
  name: string
  image_path: string
  algorithm: AlgorithmType
  feature_params?: FeatureParams
  matching_params?: MatchingParams
  mapper_params?: Record<string, any>
}

export enum BlockStatus {
  CREATED = 'created'
  QUEUED = 'queued'
  RUNNING = 'running'
  COMPLETED = 'completed'
  FAILED = 'failed'
  CANCELLED = 'cancelled'
}

export enum AlgorithmType {
  COLMAP = 'colmap'
  GLOMAP = 'glomap'
  INSTANTSFM = 'instantsfm'
  OPENMVG_GLOBAL = 'openmvg_global'
}
```

**API调用**：
```typescript
import axios from 'axios'

const BASE_URL = 'http://localhost:8000'

export const api = {
  // Blocks
  getBlocks: () =>
    axios.get<Block[]>(`${BASE_URL}/api/blocks`),

  createBlock: (data: BlockCreate) =>
    axios.post<Block>(`${BASE_URL}/api/blocks`, data),

  runBlock: (blockId: string) =>
    axios.post(`${BASE_URL}/api/blocks/${blockId}/run`),

  getBlockStatus: (blockId: string) =>
    axios.get<BlockStatus>(`${BASE_URL}/api/blocks/${blockId}/status`),
}
```

---

## API参考

### 核心端点

#### Block管理

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|--------|
| GET | `/api/blocks` | 获取所有Block | - | BlockList |
| POST | `/api/blocks` | 创建Block | BlockCreate | Block |
| GET | `/api/blocks/{id}` | 获取Block详情 | - | Block |
| PATCH | `/api/blocks/{id}` | 更新Block | BlockUpdate | Block |
| DELETE | `/api/blocks/{id}` | 删除Block | - | - |
| POST | `/api/blocks/{id}/run` | 启动SfM | - | Block |
| POST | `/api/blocks/{id}/reset` | 重置Block | - | Block |
| GET | `/api/blocks/{id}/status` | 获取状态 | - | StatusResponse |
| POST | `/api/blocks/{id}/cancel` | 取消任务 | - | Block |

#### 重建版本

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|--------|
| GET | `/api/blocks/{id}/recon-versions` | 获取版本列表 | - | ReconVersionList |
| POST | `/api/blocks/{id}/recon-versions` | 创建版本 | ReconVersionCreate | ReconVersion |
| GET | `/api/blocks/{id}/recon-versions/{vid}` | 获取版本详情 | - | ReconVersion |
| DELETE | `/api/blocks/{id}/recon-versions/{vid}` | 删除版本 | - | - |
| POST | `/api/blocks/{id}/recon-versions/{vid}/cancel` | 取消版本 | - | - |

#### 3DGS训练

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|--------|
| POST | `/api/blocks/{id}/gs/train` | 启动训练 | GSTrainParams | - |
| GET | `/api/blocks/{id}/gs/status` | 获取状态 | - | GSStatus |
| POST | `/api/blocks/{id}/gs/cancel` | 取消训练 | - | - |
| GET | `/api/blocks/{id}/gs/files` | 获取文件 | - | GSFiles |
| GET | `/api/blocks/{id}/gs/download` | 下载PLY | - | File |
| GET | `/api/blocks/{id}/gs/log` | 获取日志 | - | GSLog |

#### 3D Tiles转换

| 方法 | 端点 | 说明 | 请求体 | 响应 |
|------|------|------|--------|--------|
| POST | `/api/blocks/{id}/tiles/convert` | OpenMVS转Tiles | TilesConvertParams | - |
| GET | `/api/blocks/{id}/tiles/status` | 获取状态 | - | TilesStatus |
| GET | `/api/blocks/{id}/tiles/files` | 获取文件 | - | TilesFiles |
| POST | `/api/blocks/{id}/gs/tiles/convert` | 3DGS转Tiles | - | - |

### 数据模型

**BlockStatus**（枚举）：
```typescript
enum BlockStatus {
  CREATED = 'created'     // 刚创建，等待运行
  QUEUED = 'queued'      // 在队列中等待
  RUNNING = 'running'     // 正在处理
  COMPLETED = 'completed'  // 处理完成
  FAILED = 'failed'       // 处理失败
  CANCELLED = 'cancelled'  // 已取消
}
```

**AlgorithmType**：
```typescript
enum AlgorithmType {
  COLMAP = 'colmap'
  GLOMAP = 'glomap'
  INSTANTSFM = 'instantsfm'
  OPENMVG_GLOBAL = 'openmvg_global'
}
```

---

## WebSocket通信

### 进度更新频道

**端点**：`ws://localhost:8000/ws/blocks/{block_id}/progress`

**消息格式**：
```json
{
  "type": "stage" | "progress" | "completed" | "failed",
  "stage": "feature_extraction" | "mapping" | ...,
  "progress": 0.0-1.0,
  "message": "Processing image 1/100",
  "timestamp": "2024-02-12T10:30:00Z"
}
```

**客户端代码**：
```typescript
// 使用原生 WebSocket API
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const url = `${protocol}//${window.location.host}/ws/blocks/${blockId}/progress`

const ws = new WebSocket(url)

ws.onopen = () => {
  console.log('WebSocket connected')
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  switch (data.type) {
    case 'progress':
      updateProgressBar(data.progress)
      break
    case 'stage':
      updateCurrentStage(data.stage)
      break
    case 'completed':
      showCompletionMessage()
      break
    case 'failed':
      showErrorMessage(data.message)
      break
  }
}

ws.onerror = (error) => {
  console.error('WebSocket error:', error)
}

ws.onclose = () => {
  console.log('WebSocket disconnected')
}
```

**Vue 3 组合式函数封装**（项目中实际使用）：
```typescript
// composables/useWebSocket.ts
import { ref, onUnmounted } from 'vue'

export function useWebSocket(blockId: string) {
  const connected = ref(false)
  const progress = ref<ProgressMessage | null>(null)
  const error = ref<string | null>(null)

  let ws: WebSocket | null = null

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/blocks/${blockId}/progress`

    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as ProgressMessage
      progress.value = data
    }

    ws.onerror = () => {
      error.value = 'WebSocket connection error'
    }

    ws.onclose = () => {
      connected.value = false
      // 自动重连
      setTimeout(() => connect(), 3000)
    }
  }

  onUnmounted(() => {
    ws?.close()
  })

  return { connected, progress, error, connect }
}
```

### 可视化频道（InstantSfM）

**端点**：`ws://localhost:8000/ws/visualization/{block_id}`

**用途**：实时推送 InstantSfM 的 Viser 可视化数据

**服务端代理**：
```python
# app/ws/visualization.py

async def forward_viser_data(websocket: WebSocket, block_id: str):
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', f'http://localhost:8080/{block_id}') as r:
            async for chunk in r.aiter_bytes():
                await websocket.send_bytes(chunk)
```

---

## 测试

### 后端测试

**pytest配置**（`backend/tests/conftest.py`）：
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with AsyncSession(engine) as session:
        yield session
```

**后端测试**：
```bash
cd backend
pytest                           # 运行所有测试
pytest tests/test_config.py       # 运行配置测试
pytest -v                         # 详细输出
pytest --cov=app                  # 测试覆盖率
```

**实际测试文件**：
- `conftest.py` - Pytest 配置和 fixtures
- `test_config.py` - 配置系统测试
- `test_config_fixtures.py` - 配置 fixtures 测试

**前端测试**：

**Vitest配置**（`frontend/vitest.config.ts`）：
```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    globals: true,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
})
```

**实际测试文件**：
- `tests/components/BlockCard.test.ts` - BlockCard 组件测试
- `tests/stores/blocks.test.ts` - Blocks store 测试
- `tests/setup.ts` - 测试环境设置

**组件测试示例**：
```typescript
// tests/components/BlockCard.test.ts
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BlockCard from '@/components/BlockCard.vue'

describe('BlockCard', () => {
  it('renders block name', () => {
    const wrapper = mount(BlockCard, {
      props: {
        block: {
          id: 'test-id',
          name: 'Test Block',
          status: 'completed'
        }
      }
    })

    expect(wrapper.text()).toContain('Test Block')
  })
})
```

**运行测试**：
```bash
cd frontend
npm run test        # 运行所有测试
npm run test:ui     # 使用 Vitest UI
```

---

## 部署

### Docker部署（可选）

> **注意**：以下 Docker 配置为示例，项目根目录未包含 Dockerfile。如需 Docker 部署，请根据实际情况创建。

**后端 Dockerfile 示例**：
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**前端 Dockerfile 示例**：
```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
EXPOSE 3000

RUN npm run build

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0"]
```

**Docker Compose 示例**：
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AEROTRI_DB_PATH=/app/data/aerotri.db
    volumes:
      - ./data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

### 生产环境

**Nginx配置**：
```nginx
server {
    listen 80;
    server_name aerotri.example.com;

    # Frontend
    location / {
        root /var/www/aerotri-web/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 开发最佳实践

### 代码规范

**Python规范**（PEP 8）：
- 使用类型注解
- 函数文档字符串
- 最大行长度79（除注释）
- 类名使用PascalCase
- 函数/变量使用snake_case

**TypeScript规范**：
- 使用严格模式（`"strict": true` in tsconfig.json）
- 定义明确的接口类型
- 避免使用`any`类型
- 使用const/let而非var

**Vue规范**：
- 使用Composition API
- 组件名使用PascalCase
- Props定义明确类型
- 计算属性使用computed

### Git提交规范

**Conventional Commits**：
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型**：
- `feat`: 新功能
- `fix`: Bug修复
- `perf`: 性能优化
- `refactor`: 代码重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具链更新

**示例**：
```
feat(blocks): add partition support for large datasets

- Add partition configuration panel
- Implement partition service logic
- Update task runner to handle partitions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 调试技巧

**后端调试**：
```python
import logging

logger = logging.getLogger(__name__)

# 在关键位置添加日志
logger.info(f"Processing block {block_id}")
logger.error(f"Task failed: {error_message}")

# 使用pdb设置断点
import pdb; pdb.set_trace()
```

**前端调试**：
```typescript
console.log('Block data:', blockData)
console.error('API error:', error)

// 使用Vue DevTools
const app = document.getElementById('__app__')
console.log(app)
```

**性能分析**：
```python
# 使用cProfile分析性能
import cProfile

pr = cProfile.Profile()
pr.enable()
# ... 代码 ...
pr.disable()
pr.print_stats(sort='cumtime')
```

---

## 下一步

- [API文档](../04-algorithms/) - 完整API参考
- [用户指南](../03-user-guide/) - 功能使用说明
- [贡献指南](../07-contribution/) - 如何贡献
