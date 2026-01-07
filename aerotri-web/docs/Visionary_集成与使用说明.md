## Visionary 集成与使用说明（3DGS 高级预览）

### 1. 功能概览

- **内嵌预览（弹窗）**：在 `3DGS` 页面的「训练产物」标签中，直接在浏览器内使用 Visionary 渲染 3DGS 结果（支持 `.ply` / `.spz`）。
- **新标签页高级工具**：可在新标签页打开完整的 Visionary Simple Viewer（本地运行在 `http://localhost:3001`），进行更复杂的调试与场景管理。
- **服务器文件直连**：无需先下载到本机，通过后端下载接口直接从服务器加载 3DGS 文件。

### 2. 前提条件

- 浏览器支持 **WebGPU**（建议 Chrome / Edge 113+，或 Firefox Nightly）。
- 本地已启动：
  - `aerotri-web` 前端（默认 `http://localhost:3000`）
  - Visionary dev server（例如 `cd /root/work/visionary && npm run dev -- --port 3001`）

### 3. 在 aerotri-web 中使用 Visionary

#### 3.1 打开 3DGS 页面

1. 进入某个 block 详情页。
2. 切换到 `3DGS` 标签。
3. 在子标签中切换到 **「训练产物」**。

#### 3.2 弹窗快速预览（当前 block 的 3DGS 结果）

- 在「训练产物」卡片右上角，有按钮：
  - **在 Visionary 中预览**：\n
    - 自动选择当前 block 下最新的可预览 3DGS 文件：\n
      - 优先选择 `3dtiles/*.spz`\n
      - 若无 `.spz`，选择最新的 `model/point_cloud/iteration_*/point_cloud.ply`\n
    - 弹出大号对话框，在内部 iframe 中加载 `public/visionary/viewer.html`，并通过 `file_url` 参数传递后端下载地址。
  - **新标签页 Visionary**：\n
    - 使用同样的文件选择策略，在新标签页打开 Visionary Simple Viewer：\n
      - 默认地址：`http://localhost:3001/demo/simple/index.html?file_url=...`\n
      - 也可以通过构建时注入 `VITE_VISIONARY_SIMPLE_URL` 自定义。

- 在文件列表中，每一行如果 `类型=gaussian` 且 `preview_supported=true`：
  - 显示 **「预览」** 按钮：在弹窗中用 Visionary 打开该文件。
  - 显示 **「新标签页」** 按钮：在新标签页中用 Visionary Simple Viewer 打开该文件。

#### 3.3 弹窗中的「高级模式：自定义 URL」

- 在 Visionary 弹窗底部，有一个折叠区域：**「高级：自定义 3DGS 文件 URL（PLY / SPZ）」**。
- 用途：
  - 手动输入任意 3DGS 文件 URL（例如其他服务的下载链接）。
  - 点击「加载」后，会重新设置 iframe 的 `src` 为 `viewer.html?file_url=...`，由 Visionary 负责加载。
- 建议使用形如：

```text
/api/blocks/{block_id}/gs/download?file=model/point_cloud/iteration_7000/point_cloud.ply
/api/blocks/{block_id}/gs/download?file=3dtiles/point_cloud.spz
```

### 4. Visionary Simple Viewer 中通过 URL 自动加载

在 `visionary` 仓库的 `src/main.ts` 中，已经增加了对 URL 参数的支持：

- 当访问类似：

```text
http://localhost:3001/demo/simple/index.html?file_url=http://localhost:8000/api/blocks/{block_id}/gs/download?file=...
```

- 初始化完成后会自动执行：
  - `window.gaussianApp.loadSample(file_url)`
- 支持 `.ply` 和 `.spz`（由 Visionary 内部 loader 根据扩展名判断）。

### 5. 后端接口约定

- **列出 3DGS 文件**：`GET /api/blocks/{block_id}/gs/files`\n
  - 返回 `GSFilesResponse`，其中：\n
    - `name`: 相对路径（如 `model/point_cloud/iteration_7000/point_cloud.ply`）\n
    - `type`: `"gaussian"` / `"other"`\n
    - `preview_supported`: `true` 表示前端可用于 Visionary 预览\n
    - `download_url`: `/api/blocks/{block_id}/gs/download?file=...`

- **下载 3DGS 文件**：`GET /api/blocks/{block_id}/gs/download?file=...`\n
  - 支持 `.ply` / `.spz` / `.json` 等。\n
  - `.ply` / `.spz` 使用 `application/octet-stream`，便于 Visionary 通过 fetch 读取二进制流。\n

### 6. 测试建议

#### 6.1 功能测试

1. **本地文件验证**（已完成）：\n
   - 在 `http://localhost:3001/demo/simple/index.html` 拖拽本地 `.ply` / `.spz`，确认 Visionary 能正确显示。

2. **服务器文件快速预览**：\n
   - 在 aerotri-web 的 3DGS → 训练产物中：\n
     - 点击某个 `point_cloud.ply` 行的「预览」按钮。\n
     - 查看弹窗中是否正确加载 3DGS 模型。\n
   - 若有 `3dtiles/point_cloud.spz`：\n
     - 测试「在 Visionary 中预览」主按钮是否优先使用 `.spz`。

3. **新标签页高级预览**：\n
   - 点击行级「新标签页」按钮或卡片头部的「新标签页 Visionary」。\n
   - 确认在 `http://localhost:3001/...` 新标签页中自动加载对应文件。

4. **自定义 URL 高级模式**：\n
   - 在弹窗底部的高级区域中输入手工构造的 URL（可以故意写错），观察：\n
     - 正确 URL：成功加载。\n
     - 错误 URL：iframe 内错误弹窗提示 + 浏览器控制台有详细错误信息。

#### 6.2 异常与兼容性测试

- **WebGPU 不支持的浏览器**：\n
  - 在不支持 WebGPU 的环境中打开弹窗，应看到 WebGPU 不支持提示，而不是白屏或无限 loading。\n
- **文件不存在 / 已删除**：\n
  - 手动删除某个 PLY / SPZ 后再点预览，应出现清晰的 404 提示。\n
- **Visionary dev server 未启动**：\n
  - 对于「新标签页 Visionary」入口，应在浏览器中看到连接失败的信息，便于排查（该场景主要由开发环境处理）。\n

### 7. 配置项

- **VITE_VISIONARY_SIMPLE_URL**（可选）\n
  - 用于在构建前端时自定义 Visionary Simple Viewer 的基础地址，例如：\n

```bash
VITE_VISIONARY_SIMPLE_URL=https://your-domain/visionary/demo/simple/index.html
```

  - 若未配置，默认使用 `http://localhost:3001/demo/simple/index.html`。

