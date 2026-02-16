# 01-quickstart

## 5分钟快速体验

### 本地开发

#### 1. 启动后端

```bash
cd aerotri-web/backend

# 复制配置文件
cp config/application.yaml.example config/application.yaml

# 编辑配置，设置算法路径
vim config/application.yaml

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 启动前端（新终端）

```bash
cd aerotri-web/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

#### 3. 创建第一个重建任务

1. 访问 http://localhost:3000
2. 点击"创建Block"
3. 选择图像目录或上传图像
4. 选择算法
5. 配置参数
6. 点击"运行" 开启空三
7. 查看实时进度与Log

### 环境要求

- Python 3.10+
- Node.js 16+
- CUDA支持（推荐，用于GPU加速）
- 至少8GB内存
- 至少20GB磁盘空间

### 常见问题

**Q: 后端启动失败？**
A: 检查算法路径配置是否正确，确保COLMAP等工具已安装并在PATH中

**Q: 前端无法连接后端？**
A:
1. 检查后端是否运行在 8000 端口
2. 检查 CORS 配置（后端 `application.yaml` 中应包含前端地址）
3. 检查前端代理配置（`vite.config.mjs`）

**Q: GPU不被识别？**
A: 安装NVIDIA驱动和CUDA toolkit，确保nvidia-smi命令可用
