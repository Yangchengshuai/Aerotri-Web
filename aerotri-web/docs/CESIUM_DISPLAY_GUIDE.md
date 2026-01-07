# Cesium 倾斜模型显示指南

## 概述

本文档说明如何在 AeroTri Web 应用中显示 3D Tiles 倾斜模型。

## 显示位置

倾斜模型在以下位置显示：

1. **3D Tiles 标签页**（主要显示位置）
   - 位置：Block 详情页 → "3D Tiles" 标签
   - 行为：转换完成后自动显示 CesiumViewer
   - 组件：`TilesConversionPanel.vue` 中的 `CesiumViewer` 组件

2. **预览对话框**（备用显示方式）
   - 触发：点击转换产物中的 `tileset.json` 文件的"预览"按钮
   - 组件：`TilesConversionPanel.vue` 中的对话框

## 技术实现

### 1. 后端 API

- **获取 tileset URL**：`GET /api/blocks/{block_id}/tiles/tileset_url`
  - 返回：`{ "tileset_url": "/api/blocks/{block_id}/tiles/download?file=tileset.json" }`

- **下载文件**：`GET /api/blocks/{block_id}/tiles/download?file={filename}`
  - 支持的文件：`tileset.json`, `model.b3dm`, `model.glb`（如果保留）

### 2. 前端组件

#### TilesConversionPanel.vue
- 转换完成后自动加载并显示 CesiumViewer
- 提供"显示倾斜模型"按钮（如果未自动显示）
- 提供预览对话框功能

#### CesiumViewer.vue
- 接收 `tilesetUrl` prop
- 使用 CesiumJS 加载 3D Tiles
- 自动缩放至模型范围

### 3. 相对路径解析

`tileset.json` 中的 `model.b3dm` 是相对路径：
```json
{
  "root": {
    "content": {
      "uri": "model.b3dm"
    }
  }
}
```

Cesium 会基于 tileset.json 的 URL 解析相对路径：
- tileset.json URL: `/api/blocks/{block_id}/tiles/download?file=tileset.json`
- model.b3dm 解析为: `/api/blocks/{block_id}/tiles/download?file=model.b3dm`

这应该能够正常工作，因为后端有对应的 download 端点。

## 使用流程

1. **完成 OpenMVS 重建**
   - 确保重建状态为"已完成"
   - 确保纹理阶段已完成

2. **启动 3D Tiles 转换**
   - 在"3D Tiles"标签页点击"开始转换"
   - 等待转换完成（状态变为"已完成"）

3. **查看倾斜模型**
   - 转换完成后，CesiumViewer 会自动显示在"3D Tiles"标签页中
   - 或者点击"显示倾斜模型"按钮手动显示
   - 或者点击 `tileset.json` 的"预览"按钮在对话框中查看

## 故障排查

### 问题：模型不显示

1. **检查转换状态**
   - 确保转换状态为"已完成"
   - 检查 `tiles_output_path` 是否正确设置

2. **检查文件是否存在**
   - `tileset.json` 应该存在于 `{tiles_output_path}/tileset.json`
   - `model.b3dm` 应该存在于 `{tiles_output_path}/model.b3dm`

3. **检查浏览器控制台**
   - 查看是否有 CORS 错误
   - 查看是否有 404 错误（文件未找到）
   - 查看是否有 Cesium 加载错误

4. **检查网络请求**
   - 打开浏览器开发者工具 → Network 标签
   - 检查 tileset.json 和 model.b3dm 的请求是否成功

### 问题：相对路径解析失败

如果 Cesium 无法正确解析 `model.b3dm` 的相对路径，可以：

1. **修改 tileset.json**（临时方案）
   - 将 `"uri": "model.b3dm"` 改为绝对路径
   - 例如：`"uri": "/api/blocks/{block_id}/tiles/download?file=model.b3dm"`

2. **修改后端 API**（推荐方案）
   - 在返回 tileset.json 之前，动态修改其中的 URI
   - 将相对路径转换为绝对路径

## 测试数据

测试 Block ID: `494c3ac3-5228-4d16-ad3e-ebfcc84456cf`

测试文件位置：
- tileset.json: `/root/work/aerotri-web/data/outputs/494c3ac3-5228-4d16-ad3e-ebfcc84456cf/recon/tiles/tileset.json`
- model.b3dm: `/root/work/aerotri-web/data/outputs/494c3ac3-5228-4d16-ad3e-ebfcc84456cf/recon/tiles/model.b3dm`

## 相关文件

- 前端组件：
  - `frontend/src/components/TilesConversionPanel.vue`
  - `frontend/src/components/CesiumViewer.vue`
  - `frontend/src/views/BlockDetailView.vue`

- 后端 API：
  - `backend/app/api/tiles.py`
  - `backend/app/services/tiles_runner.py`

- 类型定义：
  - `frontend/src/types/index.ts`
  - `frontend/src/api/index.ts`

