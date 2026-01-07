# SuperSplat 集成方案

## 一、SuperSplat 简介

根据 [SuperSplat GitHub 仓库](https://github.com/playcanvas/supersplat) 和 [官方文档](https://developer.playcanvas.com/user-manual/gaussian-splatting/editing/supersplat/)：

### 1.1 特点

- ✅ **免费开源**：MIT 许可证
- ✅ **浏览器运行**：无需下载安装
- ✅ **功能完整**：检查、编辑、优化、发布 3DGS 模型
- ✅ **支持 PLY**：可以直接加载 PLY 文件
- ✅ **活跃维护**：3.4k stars，PlayCanvas 维护
- ✅ **WebGL/WebGPU**：高性能渲染

### 1.2 项目信息

- **GitHub**: https://github.com/playcanvas/supersplat
- **在线编辑器**: https://superspl.at/editor
- **文档**: https://developer.playcanvas.com/user-manual/gaussian-splatting/editing/supersplat/
- **Stars**: 3.4k
- **License**: MIT

## 二、集成方案设计

### 2.1 架构设计

```
3D Tiles (B3DM files)
    ↓
B3DM 解析器（提取 GLB）
    ↓
GLB 解析器（提取 Gaussian 数据）
    ↓
SuperSplat 渲染器
    ↓
高质量 3DGS 渲染
```

### 2.2 核心优势

1. **保持分块加载**：使用 3D Tiles 的分块优势
2. **高质量渲染**：SuperSplat 的完整 3DGS 支持
3. **快速加载**：< 10 秒初始加载
4. **按需加载**：只加载可见区域

## 三、实施步骤

### 阶段 1: 环境准备（1 天）

#### 步骤 1.1: 克隆 SuperSplat 仓库

```bash
cd /root/work
git clone https://github.com/playcanvas/supersplat.git
cd supersplat
npm install
npm run develop
```

#### 步骤 1.2: 研究 SuperSplat 架构

查看 SuperSplat 源码结构：
- `src/` - 源代码
- 查找 PLY 加载相关代码
- 查找渲染器核心代码

#### 步骤 1.3: 提取核心渲染器

从 SuperSplat 中提取：
- 渲染器核心（不包含编辑器 UI）
- PLY/Gaussian 数据加载器
- 渲染逻辑

### 阶段 2: 3D Tiles 集成（3-5 天）

#### 步骤 2.1: 实现 Tileset 加载器

```typescript
// frontend/src/utils/tilesetLoader.ts
export class TilesetLoader {
  async loadTileset(baseUrl: string): Promise<Tileset> {
    const response = await fetch(`${baseUrl}/tileset.json`)
    return await response.json()
  }
  
  async loadTile(baseUrl: string, tileUri: string): Promise<ArrayBuffer> {
    const response = await fetch(`${baseUrl}/${tileUri}`)
    return await response.arrayBuffer()
  }
  
  selectTiles(tileset: Tileset, cameraPosition: [number, number, number]): Tile[] {
    // 实现 LOD 和视锥裁剪
    return []
  }
}
```

#### 步骤 2.2: 实现 B3DM 解析器

```typescript
// frontend/src/utils/b3dmParser.ts
export class B3DMParser {
  static parse(b3dmBuffer: ArrayBuffer): { glb: ArrayBuffer } {
    // 解析 B3DM header
    // 提取 GLB
    return { glb }
  }
}
```

#### 步骤 2.3: 实现 GLB 到 Gaussian 数据转换

```typescript
// frontend/src/utils/gaussianDataExtractor.ts
export class GaussianDataExtractor {
  static extract(glbBuffer: ArrayBuffer): GaussianData {
    // 解析 GLB
    // 提取 KHR_gaussian_splatting 数据
    // 转换为 SuperSplat 格式
    return gaussianData
  }
}
```

### 阶段 3: SuperSplat 渲染器集成（5-7 天）

#### 步骤 3.1: 创建 SuperSplat Viewer 组件

```vue
<!-- frontend/src/components/SuperSplatViewer.vue -->
<template>
  <div ref="container" class="supersplat-viewer"></div>
</template>

<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import { TilesetLoader } from '@/utils/tilesetLoader'
import { B3DMParser } from '@/utils/b3dmParser'
import { GaussianDataExtractor } from '@/utils/gaussianDataExtractor'
// 导入 SuperSplat 渲染器核心

const props = defineProps<{
  tilesetUrl: string
}>()

const container = ref<HTMLDivElement | null>(null)
let renderer: any = null
let tilesetLoader: TilesetLoader

onMounted(async () => {
  if (!container.value) return
  
  // 初始化 SuperSplat 渲染器
  // renderer = new SuperSplatRenderer(container.value)
  
  // 加载 tileset
  tilesetLoader = new TilesetLoader()
  const tileset = await tilesetLoader.loadTileset(props.tilesetUrl)
  
  // 加载并渲染 tiles
  await loadAndRenderTiles(tileset)
})

async function loadAndRenderTiles(tileset: any) {
  // 选择需要加载的 tiles
  const tilesToLoad = tilesetLoader.selectTiles(tileset, [0, 0, 0])
  
  for (const tile of tilesToLoad) {
    if (tile.content?.uri) {
      // 加载 B3DM
      const b3dmBuffer = await tilesetLoader.loadTile(props.tilesetUrl, tile.content.uri)
      const { glb } = B3DMParser.parse(b3dmBuffer)
      
      // 提取 Gaussian 数据
      const gaussianData = GaussianDataExtractor.extract(glb)
      
      // 添加到 SuperSplat 渲染器
      // renderer.addGaussianData(gaussianData)
    }
  }
}

onUnmounted(() => {
  if (renderer) {
    renderer.dispose()
  }
})
</script>
```

#### 步骤 3.2: 研究 SuperSplat 源码

从 SuperSplat 仓库中提取核心渲染逻辑：

1. **查找渲染器核心**
   ```bash
   cd /root/work/supersplat
   find src -name "*render*" -o -name "*viewer*" -o -name "*splat*"
   ```

2. **查找 PLY 加载器**
   ```bash
   find src -name "*ply*" -o -name "*loader*"
   ```

3. **提取核心代码**
   - 渲染器初始化
   - Gaussian 数据加载
   - 渲染循环

### 阶段 4: 优化和测试（3-5 天）

#### 步骤 4.1: 性能优化

- 按需加载 tiles
- 实现 LOD 策略
- 缓存已加载的 tiles
- 使用 Web Workers 解析

#### 步骤 4.2: 功能测试

- Tileset 加载
- B3DM 解析
- GLB 解析
- Gaussian 数据提取
- SuperSplat 渲染

#### 步骤 4.3: 性能测试

- 初始加载时间
- 内存占用
- 帧率
- 网络请求数量

## 四、SuperSplat 源码研究

### 4.1 关键文件查找

```bash
cd /root/work/supersplat

# 查找渲染相关
find src -type f -name "*.ts" | grep -E "(render|viewer|splat)" | head -20

# 查找 PLY 加载
find src -type f -name "*.ts" | grep -E "(ply|load)" | head -20

# 查看 package.json 了解依赖
cat package.json
```

### 4.2 可能的集成方式

1. **方式 1：提取核心渲染器**
   - 从 SuperSplat 中提取渲染器核心
   - 移除编辑器 UI
   - 集成到 Vue 项目

2. **方式 2：使用 SuperSplat 作为库**
   - 如果 SuperSplat 提供 npm 包
   - 直接安装使用

3. **方式 3：参考实现**
   - 研究 SuperSplat 的实现
   - 自己实现类似的渲染器

## 五、时间估算

| 阶段 | 时间 | 说明 |
|------|------|------|
| 环境准备 | 1 天 | 克隆仓库，研究源码 |
| 3D Tiles 集成 | 3-5 天 | Tileset 加载器，B3DM/GLB 解析 |
| SuperSplat 集成 | 5-7 天 | 提取核心，集成渲染器 |
| 优化和测试 | 3-5 天 | 性能优化，功能测试 |
| **总计** | **12-18 天** | **约 2-3 周** |

## 六、参考资源

1. **SuperSplat GitHub**: https://github.com/playcanvas/supersplat
2. **SuperSplat 文档**: https://developer.playcanvas.com/user-manual/gaussian-splatting/editing/supersplat/
3. **在线编辑器**: https://superspl.at/editor
4. **3D Tiles 规范**: https://github.com/CesiumGS/3d-tiles
5. **KHR_gaussian_splatting**: https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_gaussian_splatting

## 七、下一步行动

### 立即执行

1. **确认代码修改**：min/max 已添加 ✅
2. **重新生成 3D Tiles**：使用新代码生成
3. **测试效果**：在 Cesium 中预览

### 如果仍然是黑白

1. **克隆 SuperSplat 仓库**
2. **研究源码结构**
3. **开始集成实施**
