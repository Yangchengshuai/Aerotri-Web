# Cesium 加载 3DGS（3D Gaussian Splatting）模型调研报告

## 1. 背景

用户在服务器端完成 3D Gaussian Splatting (3DGS) 训练，得到体量约 **1GB 的 PLY 文件**，希望在 **浏览器端实时/准实时可视化**。  
当前使用 Visionary 直接加载 PLY，但存在 **浏览器无法直接访问服务器文件、需要整体下载、加载慢** 等问题。

用户已有成熟的 Cesium 前端框架，用于加载倾斜摄影模型（OBJ → glTF → 3D Tiles）。

---

## 2. Cesium 对 3DGS 的总体支持结论（TL;DR）

**结论：Cesium 是目前工程化最成熟、最推荐的 3DGS Web 可视化方案之一。**

- Cesium **不直接渲染原始 PLY**
- 但 **原生支持将 3DGS PLY 转换为 3D Tiles（1.1）并流式加载**
- Cesium 已深度参与 **glTF Gaussian Splatting 扩展标准**
- 支持 **分块加载、LOD、视锥裁剪**，非常适合 1GB 级模型

---

## 3. Cesium 官方支持路径

### 3.1 Cesium Ion（强烈推荐）

Cesium Ion 已支持：

- **直接上传 3DGS 的 PLY 文件**
- 自动识别为 **Gaussian Splats**
- 自动切片生成 **3D Tiles 1.1**
- 输出 `tileset.json`
- 前端使用 `Cesium3DTileset` 即可加载

#### 优点

- ✅ 零开发成本
- ✅ 自动切片 / LOD
- ✅ 浏览器端按需加载
- ✅ 支持超大规模数据（GB 级）

#### 加载方式（前端）

```js
const tileset = await Cesium.Cesium3DTileset.fromUrl(
  ionResourceUrl
);
viewer.scene.primitives.add(tileset);
```

---

### 3.2 Cesium Ion REST API（自动化）

如果你已有自动化管线，可使用 API 上传：

- `sourceType = POINT_CLOUD`
- `gaussianSplats = true`

适合服务器侧训练完成后自动发布。

---

## 4. 离线 / 自部署方案（不依赖 Ion）

如果 **不能使用 Cesium Ion**，可采用以下路线。

---

## 5. 方案 A：PLY → glTF (Gaussian) → 3D Tiles

### 5.1 glTF Gaussian Splatting 扩展

Cesium / Khronos 已推动以下扩展：

- `KHR_gaussian_splatting`
- `KHR_gaussian_splatting_compression_spz`

glTF 中直接存储：
- 坐标
- 旋转
- 尺度
- 颜色
- 球谐系数

### 5.2 转换流程

```text
3DGS PLY
  ↓
Gaussian glTF / GLB
  ↓
glbToB3dm
  ↓
tileset.json
  ↓
Cesium 加载
```

### 5.3 工具链

- Niantic / Visionary / 社区工具：
  - `.ply → .splat / .spz`
  - `.splat → glTF (Gaussian)`
- `3d-tiles-tools`
  - `glbToB3dm`
  - `createTilesetJson`

---

## 6. 方案 B：PLY → 点云 3D Tiles（退化方案）

如果不关心高斯形态，仅作展示：

- PLY → Point Cloud 3D Tiles
- 仅保留 XYZ + RGB
- **会丢失 3DGS 的真实渲染效果**
- 不推荐作为最终方案

---

## 7. 性能与体量分析

| 项目 | 原始 PLY | Cesium 3D Tiles |
|----|----|----|
| 文件大小 | 500MB – 2GB | 通常减少 5–10 倍 |
| 加载方式 | 整体下载 | 按视野流式 |
| LOD | 无 | 有 |
| 浏览器压力 | 极大 | 可控 |

### SPZ 压缩

- PLY：~236 bytes / splat
- SPZ：~64 bytes / splat
- **体积可减少约 90%**

---

## 8. 与 Visionary 的对比

| 维度 | Visionary | Cesium |
|---|---|---|
| 是否支持直接 PLY | 是 | 否 |
| 大模型加载 | 慢 | 快（切片） |
| LOD | 无 | 有 |
| Web 工程成熟度 | 中 | 非常高 |
| 工程部署 | 偏研究 | 工程级 |

**结论**：  
Visionary 更适合研究和本地；Cesium 更适合生产级 Web 展示。

---

## 9. 推荐架构（与你现有系统最匹配）

```text
3DGS 训练（服务器）
   ↓
PLY 输出
   ↓
Cesium Ion / 离线切片
   ↓
3D Tiles (Gaussian)
   ↓
Cesium 前端（与你现有倾斜模型系统一致）
```

你当前的：

```
OBJ → glTF → 3D Tiles → Cesium
```

可以自然扩展为：

```
3DGS PLY → 3D Tiles → Cesium
```

---

## 10. 实际建议

1. **第一优先**：直接使用 **Cesium Ion 上传 PLY**
2. 若需私有化：
   - 使用 SPZ / Gaussian glTF
   - 自行切片为 3D Tiles
3. 不建议继续使用「整体 PLY 下载」的方案

---

## 11. 结论一句话版

> **Cesium + 3D Tiles 是目前 Web 端展示 3DGS 的最工程化方案，  
对于 1GB 级模型，唯一可扩展、可维护、可交付。**

