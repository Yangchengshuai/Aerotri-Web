# 3DGS PLY 到 3D Tiles 转换流程详细梳理

## 一、总体流程概览

```
3DGS 训练输出 (PLY 文件)
    ↓
[可选] PLY → SPZ 压缩
    ↓
PLY 解析 (提取 Gaussian 数据)
    ↓
空间切片 (生成多个 tiles)
    ↓
[可选] LOD 层级生成
    ↓
为每个 tile 生成 glTF/GLB (KHR_gaussian_splatting 扩展)
    ↓
GLB → B3DM 封装
    ↓
生成 tileset.json
    ↓
3D Tiles 输出 (Cesium 可加载)
```

## 二、详细流程分析

### 2.1 PLY 文件定位

**位置**: `gs_tiles_runner.py` → `_find_ply_file()`

**逻辑**:
1. 如果指定了 `iteration` 参数，查找 `model/point_cloud/iteration_{iteration}/point_cloud.ply`
2. 否则，查找所有 `iteration_*` 目录，按迭代号降序排列，返回最新的 PLY 文件

**代码位置**: `gs_tiles_runner.py:95-128`

### 2.2 PLY → SPZ 压缩（可选）

**位置**: `gs_tiles_runner.py` → `_convert_ply_to_spz()`

**工具信息**:
- **工具名称**: `ply_to_spz`
- **工具类型**: C++ 编译的可执行文件
- **工具位置**: `backend/third_party/spz/build/ply_to_spz`
- **工具源码**: `backend/third_party/spz/cli_tools/src/ply_to_spz.cpp`
- **工具版本**: SPZ 库版本 1.1.0（根据 CMakeLists.txt）

**SPZ 库信息**:
- **来源**: Niantic Labs 开源
- **仓库**: https://github.com/nianticlabs/spz
- **格式版本**: 支持版本 2 和 3
- **压缩比**: 约 10 倍（体积减少约 90%）
- **依赖**: libz (zlib)

**转换命令**:
```bash
./ply_to_spz <input.ply> <output.spz>
```

**实现细节**:
1. 检查 `ply_to_spz` 可执行文件是否存在
2. 使用 `asyncio.create_subprocess_exec` 调用工具
3. 计算压缩比并记录日志
4. ✅ **已实现**: 使用 SPZ Python bindings 加载 SPZ 文件（替代 PLY 解析）
5. ✅ **已实现**: 在 glTF 生成时使用 `KHR_gaussian_splatting_compression_spz_2` 扩展

**代码位置**: `gs_tiles_runner.py:470-533`

**SPZ Python Bindings**:
- **环境**: conda 环境 `spz-env` (Python 3.10+)
- **安装**: 运行 `backend/scripts/setup_spz_env.sh`
- **加载模块**: `backend/app/services/spz_loader.py`
- **功能**: 使用 SPZ Python bindings 加载 SPZ 文件并转换为与 PLY parser 相同的格式
- **环境支持**: 
  - 自动检测当前 Python 环境是否有 SPZ
  - 如果不可用，自动使用 conda 环境的 Python（通过 subprocess）
  - 可通过 `SPZ_PYTHON` 环境变量配置 Python 路径

### 2.3 PLY/SPZ 文件解析

**位置**: `gs_tiles_runner.py` → `parse_ply_file()` 或 `load_spz_file()`

**功能**:
- **PLY 解析**: 使用 `ply_parser.py` 解析 PLY 文件
- **SPZ 加载**: 使用 `spz_loader.py` 和 SPZ Python bindings 加载 SPZ 文件（如果启用 SPZ 压缩）
- 提取的属性：
  - `positions`: (N, 3) - 位置坐标
  - `rotations`: (N, 4) - 四元数旋转 (x, y, z, w)
  - `scales`: (N, 3) - 缩放
  - `colors`: (N, 3) - RGB 颜色（实际是 f_dc，SH 系数）
  - `alphas`: (N,) - 不透明度
  - `sh_coefficients`: (N, M) - 球谐函数系数（可选）
  - `sh_degree`: 球谐函数度数（0-3）

**SPZ 加载实现**:
- 使用 SPZ Python bindings (`spz.load_spz()`)
- 自动处理坐标系统转换（SPZ RUB → glTF LUF）
- 返回与 PLY parser 相同格式的数据字典

**代码位置**: 
- PLY 解析: `gs_tiles_runner.py:223-234`
- SPZ 加载: `gs_tiles_runner.py:211-221`, `spz_loader.py`

### 2.4 glTF Gaussian 生成

**位置**: `gltf_gaussian_builder.py` → `build_gltf_gaussian()`

**使用的扩展**:
- **扩展名称**: `KHR_gaussian_splatting`
- **压缩扩展**: `KHR_gaussian_splatting_compression_spz_2` (当使用 SPZ 压缩时)
- **扩展类型**: glTF 2.0 扩展
- **状态**: ✅ 已实现

**SPZ 压缩支持**:
- ✅ **已实现** `KHR_gaussian_splatting_compression_spz_2` 扩展
- ✅ 当 `use_spz=True` 时，glTF 使用 SPZ 压缩扩展
- ✅ SPZ 二进制数据嵌入到 glTF buffer 中
- ✅ 文件大小减少约 90%

**glTF 结构**:
```json
{
  "extensionsUsed": ["KHR_gaussian_splatting"],
  "extensionsRequired": ["KHR_gaussian_splatting"],
  "meshes": [{
    "extensions": {
      "KHR_gaussian_splatting": {
        "positions": 0,
        "rotations": 1,
        "scales": 2,
        "colors": 3,
        "alphas": 4,
        "sphericalHarmonics": 5,  // 可选
        "sphericalHarmonicsDegree": 0-3
      }
    }
  }]
}
```

**数据格式**:
- 所有数据使用 `FLOAT` (5126) 类型
- 数据存储在 GLB 的二进制 chunk 中
- 按顺序存储：positions, rotations, scales, colors, alphas, sh_coefficients

**代码位置**: `gltf_gaussian_builder.py:518-554`

### 2.5 空间切片

**位置**: `gs_tiles_runner.py` → `TilesSlicer.slice_gaussian_data()`

**功能**:
- 将大型 Gaussian 数据集切分为多个 tiles
- 每个 tile 包含最多 `max_splats_per_tile` 个 splats（默认 100,000）
- 计算每个 tile 的边界框（bounding box）

**代码位置**: `gs_tiles_runner.py:266-275`

### 2.6 LOD 层级生成（可选）

**位置**: `gs_tiles_runner.py` → `TilesSlicer.generate_lod_levels()`

**功能**:
- 生成多个细节层级（LOD）
- 默认 LOD 级别：0.5, 0.25（即 50%, 25% 的点数）
- 用于性能优化，远距离使用低细节层级

**代码位置**: `gs_tiles_runner.py:285-305`

### 2.7 GLB → B3DM 转换

**位置**: `gs_tiles_runner.py` → `_convert_gltf_to_b3dm()`

**实现方式**:
- **完全手动实现**（不使用外部工具）
- **原因**: 早期使用 `npx 3d-tiles-tools glbToB3dm` 时出现 JSON 解析错误

**B3DM 结构**:
```
[b3dm header (28 bytes)]
[feature table JSON (空)]
[feature table BIN (空)]
[batch table JSON (空)]
[batch table BIN (空)]
[GLB 数据]
```

**B3DM Header**:
- magic: "b3dm" (4 bytes)
- version: 1 (uint32)
- byteLength: 总长度 (uint32)
- featureTableJSONByteLength: 0 (uint32)
- featureTableBinaryByteLength: 0 (uint32)
- batchTableJSONByteLength: 0 (uint32)
- batchTableBinaryByteLength: 0 (uint32)

**代码位置**: `gs_tiles_runner.py:535-612`

### 2.8 tileset.json 生成

**位置**: `gs_tiles_runner.py` → `_create_tileset_json()`

**结构**:
```json
{
  "asset": {
    "version": "1.1"
  },
  "geometricError": 1000.0,
  "root": {
    "boundingVolume": {
      "box": [center_x, center_y, center_z, half_x, 0, 0, 0, half_y, 0, 0, 0, half_z]
    },
    "geometricError": 1000.0,
    "children": [
      {
        "boundingVolume": { "box": [...] },
        "geometricError": <tile_error>,
        "content": {
          "uri": "tile_{id}_L{lod}.b3dm"
        }
      }
    ]
  }
}
```

**计算逻辑**:
- 根据所有 tiles 的边界框计算根节点的边界框
- 每个 tile 的边界框从 `TileInfo.bounding_box` 获取
- 使用 box 格式（12 个浮点数）

**代码位置**: `gs_tiles_runner.py:614-722`

## 三、工具和版本信息

### 3.1 SPZ 工具

| 工具 | 位置 | 版本 | 说明 |
|------|------|------|------|
| `ply_to_spz` | `backend/third_party/spz/build/ply_to_spz` | SPZ 1.1.0 | PLY → SPZ 转换 |
| `spz_to_ply` | `backend/third_party/spz/build/spz_to_ply` | SPZ 1.1.0 | SPZ → PLY 转换 |
| `spz_info` | `backend/third_party/spz/build/spz_info` | SPZ 1.1.0 | SPZ 文件信息查看 |

**编译信息**:
- 使用 CMake 构建
- C++ 标准：C++17
- 依赖：zlib
- 构建脚本：`backend/third_party/spz/build.sh`

### 3.2 Cesium 版本

**前端 Cesium 版本**: `1.136.0`

**位置**: `frontend/package.json:17`

**Cesium 对 3DGS 的支持**:
- ✅ Cesium 1.135+ 支持 `KHR_gaussian_splatting` 扩展
- ✅ Cesium 1.135+ 支持 `KHR_gaussian_splatting_compression_spz_2` 扩展（但当前代码未使用）
- ⚠️ Cesium 1.131 支持 `khr_spz_gaussian_splats_compression`（已废弃）
- ⚠️ Cesium 1.133 废弃旧扩展，改用 `khr_spz_gaussian_splats_compression_spz_2`

**重要提示**:
- 当前代码使用的是 `KHR_gaussian_splatting`（未压缩）
- **未使用** `KHR_gaussian_splatting_compression_spz_2` 扩展
- 因此 SPZ 压缩功能虽然生成了 SPZ 文件，但**未在 glTF 中使用**

### 3.3 其他工具

**3D Tiles 工具**:
- ❌ **未使用** `3d-tiles-tools`（早期使用过，但已移除）
- ✅ 使用**手动 B3DM 封装**（Python 实现）

## 四、实现状态更新

### 4.1 SPZ 压缩功能 ✅ 已实现

**实现状态**:
1. ✅ SPZ Python bindings 已安装（conda 环境 `spz-env`）
2. ✅ SPZ 文件加载已实现（`spz_loader.py`）
3. ✅ glTF 生成时使用 `KHR_gaussian_splatting_compression_spz_2` 扩展
4. ✅ SPZ 二进制数据嵌入到 glTF buffer 中
5. ✅ 文件大小减少约 90%

**使用方法**:
1. 安装 SPZ Python bindings: 运行 `backend/scripts/setup_spz_env.sh`
2. 在转换参数中设置 `use_spz=True`
3. 系统会自动：
   - 将 PLY 转换为 SPZ
   - 使用 SPZ Python bindings 加载 SPZ 文件
   - 生成带压缩扩展的 glTF

### 4.2 坐标系统

**当前状态**:
- PLY 文件：通常使用 RDF 坐标系
- SPZ 内部：使用 RUB 坐标系
- glTF：使用 LUF 坐标系
- **当前实现未进行坐标转换**

**影响**:
- 可能导致模型方向不正确
- 需要根据实际数据验证

### 4.3 相对坐标系

**问题**:
- 3DGS 训练时未指定地理坐标
- 生成的模型是相对坐标系下的
- tileset.json 中的 transform 未设置

**影响**:
- 模型无法直接定位到地理坐标
- 需要在 Cesium 中手动调整位置

## 五、完整转换流程代码追踪

### 5.1 入口函数

**文件**: `gs_tiles_runner.py`
**函数**: `start_conversion()`
**行号**: 130-165

### 5.2 主转换流程

**文件**: `gs_tiles_runner.py`
**函数**: `_run_conversion()`
**行号**: 167-453

**阶段划分**:
1. **阶段 1** (10%): 准备转换工具，查找 PLY 文件
2. **阶段 2** (20%): PLY 解析或 SPZ 转换
3. **阶段 3** (40%): 生成 glTF Gaussian
4. **阶段 4** (60%): 空间切片
5. **阶段 5** (70-90%): LOD 生成和 B3DM 转换
6. **阶段 6** (90-100%): 生成 tileset.json

### 5.3 关键函数调用链

```
start_conversion()
  └─> _run_conversion()
      ├─> _find_ply_file()                    # 查找 PLY 文件
      ├─> _convert_ply_to_spz()                # [可选] PLY → SPZ
      ├─> parse_ply_file()                     # 解析 PLY
      ├─> build_gltf_gaussian()                # 生成 glTF
      ├─> TilesSlicer.slice_gaussian_data()    # 空间切片
      ├─> TilesSlicer.generate_lod_levels()    # [可选] LOD 生成
      ├─> build_gltf_gaussian()                # 为每个 tile 生成 GLB
      ├─> _convert_gltf_to_b3dm()              # GLB → B3DM
      └─> _create_tileset_json()               # 生成 tileset.json
```

## 六、SPZ 扩展使用说明

### 6.1 当前未使用的扩展

**扩展名称**: `KHR_gaussian_splatting_compression_spz_2`

**应该如何使用**:
```json
{
  "extensionsUsed": [
    "KHR_gaussian_splatting",
    "KHR_gaussian_splatting_compression_spz_2"
  ],
  "extensionsRequired": [
    "KHR_gaussian_splatting",
    "KHR_gaussian_splatting_compression_spz_2"
  ],
  "meshes": [{
    "extensions": {
      "KHR_gaussian_splatting": {
        "compression": {
          "extension": "KHR_gaussian_splatting_compression_spz_2",
          "buffer": 0  // 引用包含 SPZ 数据的 buffer
        }
      }
    }
  }],
  "buffers": [{
    "uri": "compressed_data.bin",  // SPZ 压缩的二进制数据
    "byteLength": <spz_file_size>
  }]
}
```

**关键点**:
- SPZ 文件是完整的 PLY → SPZ 压缩结果
- 这个 `.bin` 文件可以直接用 SPZ 工具读取
- Cesium 1.135+ 支持此扩展

### 6.2 版本兼容性

| Cesium 版本 | 支持的扩展 | 状态 |
|------------|----------|------|
| 1.131 | `khr_spz_gaussian_splats_compression` | ⚠️ 已废弃 |
| 1.133 | `khr_spz_gaussian_splats_compression_spz_2` | ⚠️ 已废弃 |
| 1.135+ | `KHR_gaussian_splatting_compression_spz_2` | ✅ 当前支持 |

**当前使用**: `KHR_gaussian_splatting`（未压缩）

## 七、建议的改进方向

### 7.1 实现 SPZ 压缩扩展支持

**优先级**: ⭐⭐⭐⭐⭐

**步骤**:
1. 编译 SPZ Python bindings（启用 `BUILD_PYTHON_BINDINGS`）
2. 实现 SPZ 文件读取功能
3. 修改 `gltf_gaussian_builder.py` 支持 SPZ 压缩扩展
4. 在 glTF 生成时使用 SPZ 数据而不是原始 PLY 数据

**预期效果**:
- 文件体积减少约 90%
- 加载速度提升
- 带宽使用减少

### 7.2 坐标系统转换

**优先级**: ⭐⭐⭐

**步骤**:
1. 确认 PLY 文件的坐标系统
2. 实现坐标转换（PLY → glTF）
3. 在 tileset.json 中添加 transform（如果需要地理定位）

### 7.3 地理坐标支持

**优先级**: ⭐⭐

**步骤**:
1. 在 3DGS 训练时记录地理坐标信息
2. 在 tileset.json 中设置正确的 transform
3. 支持 WGS84 坐标系统

## 八、总结

### 8.1 当前实现状态

✅ **已实现**:
- PLY 文件定位和解析
- SPZ 文件生成和加载（使用 Python bindings）
- glTF Gaussian 生成（支持压缩扩展）
- `KHR_gaussian_splatting_compression_spz_2` 扩展支持
- 空间切片和 LOD 生成
- B3DM 封装
- tileset.json 生成

⚠️ **待优化**:
- 坐标系统转换（当前使用默认转换，可能需要根据实际数据调整）
- 地理坐标定位（模型是相对坐标系）

### 8.2 工具版本总结

| 工具/库 | 版本 | 位置 | 状态 |
|---------|------|------|------|
| SPZ 库 | 1.1.0 | `backend/third_party/spz` | ✅ 已编译 |
| ply_to_spz | 1.1.0 | `backend/third_party/spz/build/ply_to_spz` | ✅ 可用 |
| Cesium | 1.136.0 | `frontend/node_modules/cesium` | ✅ 已安装 |
| Python | 3.8+ | 系统 | ✅ 运行中 |

### 8.3 关键发现

1. **SPZ 压缩功能已实现但未使用**: 虽然可以生成 SPZ 文件，但 glTF 生成仍使用原始 PLY 数据
2. **Cesium 版本兼容**: 使用 Cesium 1.136.0，支持最新的扩展，但代码未使用压缩扩展
3. **B3DM 封装**: 完全手动实现，避免了外部工具的 JSON 解析问题
4. **相对坐标系**: 当前模型是相对坐标系，未设置地理坐标

---

**文档生成时间**: 2025-01-07
**代码版本**: 基于当前代码库分析
