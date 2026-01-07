# Cesium 倾斜模型查看解决方案

## 问题分析

模型使用局部坐标系（模型空间），没有地理参考信息：
- 中心点：`(0.607, -1.544, -0.803)` - 局部坐标
- 半径：约 `5.5` 单位
- 结果：模型可能在地球外很远的位置，或者在地球中心但太小看不到

## 解决方案对比

### 方案 1：禁用地球和地形，只显示模型（推荐 ⭐⭐⭐⭐⭐）

**实现方式：**
- 禁用地球（globe）
- 禁用地形（terrain）
- 禁用底图（imagery）
- 使用黑色背景，只显示模型

**优点：**
- ✅ 最简单直接，不依赖地理坐标
- ✅ 性能最好，不需要渲染地球
- ✅ 模型清晰可见，不受地球遮挡
- ✅ 适合纯模型查看场景
- ✅ 相机控制简单，直接定位到模型

**缺点：**
- ❌ 没有地理参考，无法知道模型在地球上的位置
- ❌ 失去 Cesium 的地球视图优势

**适用场景：** ✅ 只查看模型，不需要地理参考（当前需求）

---

### 方案 2：将模型 Transform 到地球中心附近

**实现方式：**
- 保持地球和地形
- 在 tileset 上应用 transform 矩阵
- 将模型移动到地球中心（0,0,0）或指定位置

**优点：**
- ✅ 保持地球视图
- ✅ 模型可以在地球上显示
- ✅ 可以添加地理参考（如果知道位置）

**缺点：**
- ❌ 需要计算 transform 矩阵
- ❌ 模型可能被地球遮挡
- ❌ 如果模型太大，可能穿透地球
- ❌ 性能稍差（需要渲染地球）

**适用场景：** 需要在地球上显示模型，且知道大致位置

---

### 方案 3：使用局部坐标系模式（Scene Mode）

**实现方式：**
- 使用 `SCENE2D` 或 `COLUMBUS_VIEW` 模式
- 禁用地球，使用平面视图
- 相机直接定位到模型

**优点：**
- ✅ 保持 Cesium 的相机控制
- ✅ 可以切换回 3D 模式
- ✅ 模型清晰可见

**缺点：**
- ❌ 失去 3D 地球视图
- ❌ 2D 模式可能不适合倾斜模型查看

**适用场景：** 需要平面视图查看模型

---

### 方案 4：改进相机定位逻辑（当前方案改进）

**实现方式：**
- 保持地球和地形
- 改进 `zoomToModel` 函数
- 使用 `viewBoundingSphere` 强制定位
- 添加距离和角度调整

**优点：**
- ✅ 保持地球视图
- ✅ 改进定位逻辑
- ✅ 可以调整视角

**缺点：**
- ❌ 如果模型太远，可能还是看不到
- ❌ 需要精确计算相机位置
- ❌ 性能可能较差（渲染地球）

**适用场景：** 模型有地理参考，但定位不准确

---

## 推荐方案

**根据当前需求（只查看模型，不管绝对位置），推荐使用方案 1：禁用地球和地形**

### 实现步骤

1. 禁用地球：`viewer.scene.globe.show = false`
2. 禁用地形：使用 `EllipsoidTerrainProvider` 或禁用
3. 禁用底图：`viewer.imageryLayers.removeAll()`
4. 设置黑色背景：`viewer.scene.backgroundColor = Cesium.Color.BLACK`
5. 直接定位到模型：使用 `viewBoundingSphere` 或 `zoomTo`

### 代码示例

```javascript
// 禁用地球
viewer.scene.globe.show = false

// 禁用底图
viewer.imageryLayers.removeAll()

// 设置黑色背景
viewer.scene.backgroundColor = Cesium.Color.BLACK

// 定位到模型
const boundingSphere = tileset.boundingSphere
viewer.camera.viewBoundingSphere(
  boundingSphere,
  new Cesium.HeadingPitchRange(0, -0.5, boundingSphere.radius * 2)
)
```

---

## 其他优化建议

1. **添加模型信息显示**：显示模型的 bounding box、顶点数等
2. **添加相机控制**：前进、后退、旋转等
3. **添加模型统计**：文件大小、加载时间等
4. **添加截图功能**：可以导出模型截图
5. **添加测量工具**：可以测量模型尺寸

