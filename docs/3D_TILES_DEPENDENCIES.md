# 3D Tiles 转换依赖诊断报告

## 问题概述

重建管线成功运行后，在进行 3D Tiles 转换时报错：
- **阶段**: `obj_to_glb`
- **错误**: `[Errno 2] No such file or directory`
- **原因**: 缺少必需的工具依赖

## 当前工具状态

### ✅ 已安装的工具

| 工具 | 状态 | 路径 | 版本 |
|------|------|------|------|
| **obj2gltf** | ✅ 已安装 | `/root/.nvm/versions/node/v24.13.0/bin/obj2gltf` | 3.2.0 |
| **exiftool** | ✅ 已安装 | `/usr/bin/exiftool` | - |
| **tensorboard** | ✅ 已安装 | Python package | 2.14.0 |
| **gltf-pipeline** | ✅ 已安装 | npm global package | - |

### ❌ 缺失的工具

| 工具 | 状态 | 原因 | 影响 |
|------|------|------|------|
| **3d-tiles-tools** | ❌ 未安装 | 网络问题导致 native 模块编译失败 | **无法创建 tileset.json** |
| **gltf-to-3d-tiles** (Python) | ❌ 未安装 | PyPI 网络连接失败 | 无直接替代方案 |

## 3D Tiles 转换流程

### 标准流程（当前实现）

```
OpenMVS OBJ (scene_dense_texture.obj)
    ↓
[obj2gltf] → GLB (model.glb)
    ↓
[gltfToB3dm] → B3DM (model.b3dm)
    ↓
[createTilesetJson] → tileset.json
    ↓
3D Tiles 输出
```

### 当前问题

`createTilesetJson` 命令来自 `3d-tiles-tools` npm 包，该包包含需要编译的 native 模块（better-sqlite3），由于网络问题无法下载编译所需的 Node.js headers。

## 解决方案

### 方案 1: 代理安装（推荐）

如果可以配置代理或使用镜像：

```bash
# 设置 npm 镜像（如果可用）
npm config set registry https://registry.npmmirror.com

# 尝试重新安装
npm install -g 3d-tiles-tools
```

### 方案 2: 手动创建 tileset.json

对于简单的 3D Tiles 场景，可以手动创建 tileset.json：

```json
{
  "asset": {
    "version": "1.0"
  },
  "geometricError": 500,
  "root": {
    "boundingVolume": {
      "box": [
        0, 0, 0,
        100, 0, 0,
        0, 100, 0,
        0, 0, 100
      ]
    },
    "geometricError": 500,
    "refine": "ADD",
    "content": {
      "uri": "model.b3dm"
    }
  }
}
```

### 方案 3: 使用 Cesium ion 在线服务

1. 上传 GLB 文件到 Cesium ion
2. 使用 Cesium ion 的 3D Tiles 服务
3. 前端直接从 ion 加载

### 方案 4: 替换为纯 Python 实现

考虑使用纯 Python 的 3D Tiles 生成库：

```python
# py3dtiles - Python 3D Tiles library
pip install py3dtiles

# 使用 py3dtiles 生成 tileset
from py3dtiles import Tileset

tileset = Tileset()
tileset.from_glb("model.glb")
tileset.write("tileset.json")
```

### 方案 5: 使用 glTF 转 3D Tiles 的其他工具

1. **Cesium ion CLI**
   ```bash
   npm install -g ion-cli
   ion-cli asset upload --token YOUR_TOKEN model.glb
   ```

2. **gltf-to-3d-tiles (TypeScript)**
   ```bash
   git clone https://github.com/CesiumGS/gltf-to-3d-tiles.git
   cd gltf-to-3d-tiles
   npm install
   npm run build
   node dist/cli.js model.glb -o tiles
   ```

## 临时解决方案

### 修改 tiles_runner.py 跳过 createTilesetJson

```python
async def _create_tileset(self, ...):
    # ... existing code for GLB → B3DM conversion ...

    # Instead of:
    # await self._create_tileset_json(...)

    # Generate minimal tileset.json:
    tileset_path = tiles_output_dir / "tileset.json"
    import json
    tileset = {
        "asset": {"version": "1.0"},
        "geometricError": 500,
        "root": {
            "boundingVolume": {"box": [/* calculated from B3DM */]},
            "geometricError": 500,
            "refine": "ADD",
            "content": {"uri": "model.b3dm"}
        }
    }
    with open(tileset_path, 'w') as f:
        json.dump(tileset, f, indent=2)
```

### 简化 3D Tiles 输出

直接使用 GLB 格式（Cesium 也支持直接加载 GLB）：

```javascript
// 前端 Cesium 代码
const tileset = await Cesium.Cesium3DTileset.fromUrl(
    './model.glb'  // 直接使用 GLB
);
```

## 推荐行动步骤

### 短期（立即可用）

1. **方案 2 + 方案 6**: 修改代码手动创建简化的 tileset.json，或直接使用 GLB 格式

2. **验证 OBJ → GLB 转换**:
   ```bash
   cd /root/work/aerotri-web/data/outputs/7a7a2dbe-999e-4729-a5b1-110e0be824d9/recon/v3
   /root/.nvm/versions/node/v24.13.0/bin/obj2gltf -i dense/scene_dense_texture.obj -o model.glb --binary
   ```

### 中期（需要网络访问）

1. 配置 npm 镜像或代理
2. 安装 3d-tiles-tools
3. 完整测试转换流程

### 长期（架构改进）

1. 考虑集成纯 Python 的 3D Tiles 生成方案
2. 添加对 Cesium ion 的支持
3. 实现更简单的 GLB 直接加载路径

## 相关文件

- `backend/app/services/tiles_runner.py` - 3D Tiles 转换实现
- `docs/3D_TILES_DEPENDENCIES.md` - 本文档
- `tools/install_3d_tiles_dependencies.sh` - 安装脚本

## 测试命令

```bash
# 测试 obj2gltf 转换
obj2gltf -i /path/to/model.obj -o /path/to/output.glb --binary

# 测试 GLB 加载（Cesium）
# 在浏览器控制台运行:
const viewer = new Cesium.Viewer('cesiumContainer');
viewer.scene.primitives.add(await Cesium.Model.fromGltfAsync({
    url: './model.glb'
}));
```

## 总结

当前 **obj2gltf** 已成功安装，可以完成 OBJ → GLB 的转换。

主要问题在于 **3d-tiles-tools** 无法安装，导致无法生成标准的 tileset.json。

**推荐方案**: 修改代码以支持简化的 tileset.json 生成，或直接使用 GLB 格式输出（Cesium 原生支持）。
