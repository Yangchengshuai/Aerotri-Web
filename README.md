# colmap_glomap 项目总览

本仓库用于汇总 **COLMAP/GLOMAP 源码** 与配套的 **AeroTri Web（网页端空三工具）**。

- **COLMAP**：增量式 SfM（空三）与 MVS 工具链（本仓库内路径：`colmap/`）
- **AeroTri Web**：面向空三调参与批处理的 Web 应用（本仓库内路径：`aerotri-web/`）

> 备注：为避免把本机/服务器上的数据集、重建输出、`node_modules` 等大文件推到仓库，已在根目录提供 `.gitignore`。

## 目录结构

```
work/
├── colmap/                 # COLMAP 源码（已脱离子仓库形式，作为普通目录提交）
├── aerotri-web/            # Web 应用：FastAPI 后端 + Vue3 前端
└── docs/                   # 本项目说明/使用/开发文档
```

## 文档

- **项目说明文档**：`docs/项目说明文档.md`
- **项目使用文档**：`docs/项目使用文档.md`
- **项目开发文档**：`docs/项目开发文档.md`

## 快速开始（AeroTri Web）

### 后端

```bash
cd aerotri-web/backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd aerotri-web/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

访问：`http://<server-ip>:5173`

## 许可证

- `colmap/` 目录遵循其上游项目 LICENSE/协议。
- `aerotri-web/` 目录为本项目 Web 工具部分，遵循其目录下声明（如有）。
