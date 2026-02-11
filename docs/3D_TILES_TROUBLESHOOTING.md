# 3D Tiles 转换问题解决方案

## 问题描述

`3d-tiles-tools` 安装失败，错误信息：
```
Something went wrong installing the "sharp" module
Cannot find module '../build/Release/sharp-linux-x64.node'
```

**根本原因**: `sharp` 是一个需要 C++ 编译的原生模块，依赖 Node.js headers 进行编译。

## 可行的解决方案

### 方案 1: 使用预编译的 sharp（推荐）⭐

`sharp` 提供了预编译的二进制文件，可以直接安装：

```bash
cd /root/work/Aerotri-Web/CesiumGS/3d-tiles-tools

# 卸载现有 sharp
npm uninstall sharp

# 安装预编译版本（指定平台）
npm install sharp@0.32.6 --platform=linux --arch=x64 --libc=glibc
```

然后测试：
```bash
npx ts-node src/cli/main.ts createTilesetJson --help
```

### 方案 2: 跳过 3D Tiles 转换，直接使用 GLB ✅

Cesium 完全支持直接加载 GLB 格式，无需转换为 3D Tiles：

**前端修改**：
```javascript
// 不使用 3D Tiles，直接加载 GLB
const viewer = new Cesium.Viewer('cesiumContainer');
const model = viewer.scene.primitives.add(
    await Cesium.Model.fromGltfAsync({
        url: '/api/blocks/7a7a2dbe-999e-4729-a5b1-110e0be824d9/recon/v3/tiles/model.glb'
    })
);
```

**优点**：
- 简单直接，无需额外工具
- GLB 文件已经通过 obj2gltf 成功生成
- Cesium 原生支持，性能良好

### 方案 3: 使用简化版 tileset.json 生成 ✅

修改 `tiles_runner.py`，移除对 `3d-tiles-tools` 的依赖，直接生成基础 tileset.json：

```python
# 在 _convert_glb_to_tiles 方法中
async def _convert_glb_to_tiles(self, glb_path, tiles_output_dir, log_buffer, log_path):
    """简化版：只生成 GLB，不生成 B3DM，手动创建 tileset.json"""
    import json
    import shutil

    # 1. 复制 GLB 到输出目录
    shutil.copy2(glb_path, tiles_output_dir / "model.glb")

    # 2. 生成基础 tileset.json
    tileset = {
        "asset": {
            "version": "1.0"
        },
        "geometricError": 500,
        "root": {
            "boundingVolume": {
                "box": [
                    0, 0, 0,      # 中心
                    100, 0, 0,    # X 半轴
                    0, 100, 0,    # Y 半轴
                    0, 0, 100     # Z 半轴
                ]
            },
            "geometricError": 500,
            "refine": "ADD",
            "content": {
                "uri": "model.glb"
            }
        }
    }

    tileset_path = tiles_output_dir / "tileset.json"
    with open(tileset_path, 'w') as f:
        json.dump(tileset, f, indent=2)

    log_buffer.append(f"Created tileset.json at {tileset_path}")
```

### 方案 4: 使用 Docker 容器 🐳

如果本地环境有问题，可以在 Docker 中运行转换：

```dockerfile
FROM node:20-alpine

RUN apk add --no-cache git python3 make g++
WORKDIR /app

# 克隆并安装 3d-tiles-tools
RUN git clone https://github.com/CesiumGS/3d-tiles-tools.git
RUN cd 3d-tiles-tools && npm install

# 挂载输入输出目录
# docker run -v $(pwd)/data:/data -v $(pwd)/output:/output 3d-tiles-container \
#   npx ts-node 3d-tiles-tools/src/cli/main.ts createTilesetJson -i /data/model.glb -o /output/
```

### 方案 5: 使用在线服务 ☁️

**Cesium ion**：NVIDIA 提供的在线 3D Tiles 服务

1. 访问 https://cesium.com/ion/
2. 上传 GLB 文件
3. 获取 3D Tiles URL
4. 在前端直接使用

## 推荐步骤

### 立即可用的方案（方案 2）

1. **确认 GLB 文件已生成**：
   ```bash
   ls -lh /root/work/aerotri-web/data/outputs/7a7a2dbe-999e-4729-a5b1-110e0be824d9/recon/v3/tiles/model.glb
   ```

2. **修改前端代码**，直接加载 GLB：
   ```vue
   <!-- 在 CesiumViewer.vue 中 -->
   <template>
     <div id="cesiumContainer" ref="cesiumContainer"></div>
   </template>

   <script setup>
   import * as Cesium from 'cesium'

   async function loadModel() {
     const viewer = new Cesium.Viewer('cesiumContainer')

     // 直接加载 GLB（无需 3D Tiles）
     const model = viewer.scene.primitives.add(
       await Cesium.Model.fromGltfAsync({
         url: '/api/blocks/7a7a2dbe-999e-4729-a5b1-110e0be824d9/recon/v3/tiles/model.glb',
         modelMatrix: Cesium.Matrix4.fromTranslation(
           new Cesium.Cartesian3(0, 0, 0)
         )
       })
     )

     viewer.zoomTo(model, new Cesium.HeadingPitchRange(0, -Math.PI / 2, 0))
   }
   </script>
   ```

3. **跳过 3D Tiles 转换**，在 UI 中标记为 "GLB 格式可用"

### 长期解决方案（方案 1）

尝试修复 sharp 安装：

```bash
cd /root/work/Aerotri-Web/CesiumGS/3d-tiles-tools

# 清理并重装
rm -rf node_modules/sharp
rm -rf package-lock.json
npm install sharp@0.32.6 --platform=linux --arch=x64 --libc=glibc

# 如果仍然失败，尝试全局安装
npm install -g sharp@0.32.6 --platform=linux --arch=x64
export SHARP_GLOBAL_BASE=/root/.npm-global/lib/node_modules/sharp
```

## 总结

| 方案 | 难度 | 效果 | 推荐度 |
|------|------|------|--------|
| **方案 1: 预编译 sharp** | 中 | 完整 3D Tiles | ⭐⭐⭐⭐ |
| **方案 2: 直接使用 GLB** | 低 | GLB 格式 | ⭐⭐⭐⭐⭐ |
| **方案 3: 简化 tileset.json** | 中 | 基础 3D Tiles | ⭐⭐⭐ |
| **方案 4: Docker** | 中 | 完整 3D Tiles | ⭐⭐⭐ |
| **方案 5: Cesium ion** | 低 | 完整 3D Tiles | ⭐⭐⭐ |

**推荐**：先使用方案 2（直接 GLB）快速验证，然后尝试方案 1（修复 sharp）获得完整 3D Tiles 支持。
