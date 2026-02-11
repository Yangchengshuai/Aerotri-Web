# 01-quickstart

## 5分钟快速体验

### Docker快速启动（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-org/aerotri-web.git
cd aerotri-web

# 使用Docker Compose启动
docker-compose up -d

# 访问应用
open http://localhost:8000
```

### 本地开发

#### 1. 启动后端

```bash
cd aerotri-web/backend

# 复制配置文件
cp config/settings.yaml.example config/settings.yaml

# 编辑配置，设置算法路径
vim config/settings.yaml

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
4. 选择算法（推荐COLMAP）
5. 配置参数（使用默认值即可）
6. 点击"开始重建"
7. 查看实时进度

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
A: 检查后端是否运行在8000端口，前端配置的代理是否正确

**Q: GPU不被识别？**
A: 安装NVIDIA驱动和CUDA toolkit，确保nvidia-smi命令可用
