# Cesium 局部坐标系模型显示问题修复

## 问题描述

倾斜模型在 Cesium 中可以正常加载，但是没有显示出来。原因是 **模型使用的是局部坐标系（模型空间），而不是地理坐标系**。

### 问题分析

检查 `tileset.json` 中的 `boundingVolume`：

```json
{
  "root": {
    "boundingVolume": {
      "box": [
        0.607451, -1.544259, -0.803140,  // 中心点（局部坐标）
        3.584955, 2.266525, -3.524285,  // 半轴长度
        ...
      ]
    }
  }
}
```

**关键发现：**
- 中心点坐标：`(0.6, -1.5, -0.8)` - 这是局部坐标，不是地理坐标
- 半径：约 `5.5` 单位 - 地理坐标应该是数百万米的数量级
- ⚠️ **模型没有地理参考信息**

### 为什么看不到模型？

1. **坐标系统不匹配**：模型在局部坐标系中，而 Cesium 期望地理坐标
2. **位置可能在地球中心**：局部坐标 `(0,0,0)` 对应地球中心
3. **模型太小**：在默认视角（全球视图）下，5.5 单位的模型太小，看不到

## 解决方案

### 1. 代码改进

已更新 `CesiumViewer.vue`，添加了以下功能：

- **自动检测局部坐标**：检测 bounding sphere 的半径和中心点
- **智能相机定位**：即使没有地理参考，也能尝试定位到模型
- **手动定位按钮**：添加"定位到模型"按钮，可以手动定位

### 2. 使用方法

1. **自动定位**：模型加载完成后，会自动尝试定位到模型
2. **手动定位**：如果看不到模型，点击右上角的"定位到模型"按钮
3. **查看控制台**：打开浏览器开发者工具，查看控制台日志：
   - `⚠️ Tileset appears to be in local/model coordinates` - 确认是局部坐标
   - `Model position:` - 查看模型的实际位置

### 3. 长期解决方案

要彻底解决这个问题，需要在转换过程中添加地理参考信息：

#### 方案 A：在 OBJ 转换时添加地理信息

如果原始数据有 GPS 信息，可以在 `obj2gltf` 或 `3d-tiles-tools` 转换时指定：

```bash
# 如果知道模型的地理位置（例如：经度 120.0，纬度 30.0，高度 100）
# 需要在转换时添加 transform 矩阵
```

#### 方案 B：在 tileset.json 中添加 transform

修改 `tileset.json`，在 root 节点添加 `transform` 矩阵：

```json
{
  "root": {
    "transform": [
      1, 0, 0, longitude,
      0, 1, 0, latitude,
      0, 0, 1, height,
      0, 0, 0, 1
    ],
    "boundingVolume": { ... }
  }
}
```

#### 方案 C：使用 Cesium 的 Entity API

如果知道模型的地理位置，可以在前端代码中设置：

```javascript
// 假设模型应该在经度 120.0，纬度 30.0
const longitude = 120.0
const latitude = 30.0
const height = 100.0

// 创建 transform 矩阵
const transform = Cesium.Matrix4.fromTranslation(
  Cesium.Cartesian3.fromDegrees(longitude, latitude, height)
)

// 应用 transform
tileset.root.transform = transform
```

## 当前状态

✅ **已修复**：
- 代码可以检测局部坐标
- 自动尝试定位到模型
- 添加了手动定位按钮
- 改进了错误处理和日志

⚠️ **待改进**：
- 需要获取原始数据的地理位置信息
- 需要在转换流程中添加地理参考
- 或者在前端代码中手动设置模型位置

## 测试建议

1. 刷新页面，查看控制台日志
2. 如果看到 `⚠️ Tileset appears to be in local/model coordinates`，说明检测正确
3. 点击"定位到模型"按钮，查看是否能定位到模型
4. 如果模型在地球中心附近，尝试缩小视图（鼠标滚轮）
5. 检查模型是否真的加载了（可能在视野之外）

## 相关文件

- `/root/work/aerotri-web/frontend/src/components/CesiumViewer.vue` - 主要修复文件
- `/root/work/aerotri-web/data/outputs/494c3ac3-5228-4d16-ad3e-ebfcc84456cf/recon/tiles/tileset.json` - tileset 配置文件

