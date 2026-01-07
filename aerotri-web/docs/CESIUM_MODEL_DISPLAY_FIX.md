# Cesium 模型显示问题修复指南

## 问题描述

显示"已定位到模型"，但页面是黑色的，看不到模型。

## 根本原因

1. **URI 路径解析问题**：`tileset.json` 中的 `uri` 是相对路径 `"model.b3dm"`，当 Cesium 从查询参数 URL 加载时，可能无法正确解析相对路径。

2. **模型可能已加载但不可见**：
   - 相机位置不对
   - 模型太小或太大
   - 模型在视野范围外

## 已实施的修复

### 1. 后端 API 修复 ✅

**文件**：`backend/app/api/tiles.py`

**修改内容**：
- 在返回 `tileset.json` 时，动态修改其中的相对路径 URI 为绝对路径
- 将 `"uri": "model.b3dm"` 改为 `"uri": "/api/blocks/{block_id}/tiles/download?file=model.b3dm"`

**代码逻辑**：
```python
if file == "tileset.json":
    # 读取 tileset.json
    # 修改 root.content.uri 为绝对路径
    # 返回修改后的 JSON
```

### 2. 前端调试增强 ✅

**文件**：`frontend/src/components/CesiumViewer.vue`

**添加的功能**：
- 详细的调试日志（控制台输出）
- 事件监听器（tileLoad, tileFailed, allTilesLoaded）
- "模型信息"按钮（显示模型状态）
- 改进的相机定位逻辑（针对小模型使用更大的范围倍数）

### 3. 禁用地球和地形 ✅

- 禁用地球：`viewer.scene.globe.show = false`
- 禁用底图：`viewer.imageryLayers.removeAll()`
- 黑色背景：`viewer.scene.backgroundColor = Cesium.Color.BLACK`
- 禁用天空盒、太阳、月亮等

## 使用步骤

### 1. 重启后端服务

后端代码已修改，需要重启才能生效：

```bash
# 如果使用 uvicorn
cd /root/work/aerotri-web/backend
# 重启服务
```

### 2. 刷新前端页面

清除浏览器缓存并刷新页面（Ctrl+Shift+R 或 Cmd+Shift+R）

### 3. 查看调试信息

打开浏览器开发者工具（F12），查看：

**Console 标签**：
- `Tileset URL:` - tileset.json 的 URL
- `Tileset debug info:` - tileset 的详细信息
- `Tileset bounding sphere:` - 模型的边界球信息
- `✓ Tile loaded:` - 模型加载成功
- `✗ Tile failed to load:` - 模型加载失败（如果有）

**Network 标签**：
- 检查 `tileset.json` 请求，查看返回的 URI 是否已修改为绝对路径
- 检查 `model.b3dm` 请求是否成功（状态码 200）

### 4. 使用调试工具

- **点击"定位到模型"按钮**：手动定位到模型
- **点击"模型信息"按钮**：查看模型的详细信息（输出到控制台）
- **点击"重置视角"按钮**：重置相机位置

## 故障排查

### 问题 1：URI 没有被修改

**检查**：
```bash
curl "http://localhost:8000/api/blocks/{block_id}/tiles/download?file=tileset.json" | jq '.root.content.uri'
```

**应该返回**：
```json
"/api/blocks/{block_id}/tiles/download?file=model.b3dm"
```

**如果不是**：
- 确认后端服务已重启
- 检查后端日志是否有错误

### 问题 2：model.b3dm 请求失败

**检查 Network 标签**：
- 查看 `model.b3dm` 请求的状态码
- 如果是 404，检查文件是否存在
- 如果是 405，检查后端路由配置

### 问题 3：模型加载但看不到

**可能原因**：
1. 相机位置不对
2. 模型太小（半径 < 10）
3. 模型在视野范围外

**解决方法**：
1. 点击"模型信息"按钮，查看模型位置和相机位置
2. 手动调整相机（鼠标拖拽、滚轮缩放）
3. 检查控制台日志中的 `Camera position after zoom`

### 问题 4：控制台显示错误

**常见错误**：
- `Failed to load tile` - 模型文件加载失败
- `CORS error` - 跨域问题
- `404 Not Found` - 文件不存在

**解决方法**：
- 检查后端服务是否运行
- 检查文件路径是否正确
- 检查 CORS 配置

## 预期结果

修复后，应该能够：

1. ✅ 看到模型在黑色背景中显示
2. ✅ 点击"定位到模型"能正确定位
3. ✅ 控制台显示详细的调试信息
4. ✅ Network 标签显示 `model.b3dm` 成功加载（200 状态码）

## 如果仍然看不到模型

1. **检查浏览器控制台**：查看是否有错误信息
2. **检查 Network 标签**：确认 `model.b3dm` 是否成功加载
3. **点击"模型信息"按钮**：查看模型的实际位置
4. **尝试手动调整相机**：使用鼠标拖拽和滚轮
5. **检查模型文件**：确认 `model.b3dm` 文件是否完整（198MB）

## 相关文件

- `backend/app/api/tiles.py` - 后端 API（已修复 URI 路径）
- `frontend/src/components/CesiumViewer.vue` - 前端组件（已添加调试功能）
- `data/outputs/494c3ac3-5228-4d16-ad3e-ebfcc84456cf/recon/tiles/tileset.json` - tileset 配置文件

