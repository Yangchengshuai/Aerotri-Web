# 02-installation

详细的安装指南，帮助您在本地环境中部署 AeroTri-Web。

## 目录

- [系统要求](#系统要求)
- [前置依赖](#前置依赖)
- [后端安装](#后端安装)
- [前端安装](#前端安装)
- [算法安装](#算法安装)
- [配置](#配置)
- [验证安装](#验证安装)
- [故障排查](#故障排查)

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4核心 | 8核心+ |
| 内存 | 8GB | 32GB+ |
| 存储 | 20GB可用空间 | 100GB+ SSD |
| GPU | 无（仅CPU模式） | NVIDIA GPU 8GB+ VRAM |

### 操作系统

- **Linux**: Ubuntu 20.04+, CentOS 7+
- **Windows**: WSL2 推荐
- **macOS**: 10.15+（部分算法可能需要调整）

### 软件要求

- **Python**: 3.10 或更高版本
- **Node.js**: 16.0 或更高版本
- **CUDA**: 11.0+（GPU加速，可选）
- **Git**: 用于克隆仓库

---

## 前置依赖

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    git \
    cmake \
    libeigen3-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    libimage-exiftool-perl \
    python3-dev \
    python3-pip \
    python3-venv \
    nodejs \
    npm
```

### CentOS/RHEL

```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    git \
    cmake \
    eigen3-devel \
    cairo-devel \
    pango-devel \
    glib2-devel \
    perl-Image-ExifTool \
    python3-devel \
    python3-pip \
    nodejs \
    npm
```

### macOS

```bash
brew install cmake eigen exiftool node python3
```

---

## 后端安装

### 1. 克隆仓库

```bash
git clone https://github.com/Yangchengshuai/Aerotri-Web.git
cd Aerotri-Web/aerotri-web
```

### 2. 创建Python虚拟环境（推荐）

```bash
cd aerotri-web/backend
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装Python依赖

```bash
# 核心依赖
pip install fastapi uvicorn sqlalchemy pydantic aiofiles python-multipart

# 图像处理和科学计算
pip install numpy scipy opencv-python pyproj

# GPU监控（可选）
pip install pynvml

# 通知服务（可选）
pip install requests

# 开发依赖（可选）
pip install pytest pytest-asyncio black
```

### 4. 配置后端

```bash
cd backend/config
cp application.yaml.example application.yaml
vim application.yaml  # 编辑配置
```

**必需配置项**：
```yaml
algorithms:
  colmap:
    path: "/usr/local/bin/colmap"  # 修改为实际路径
  glomap:
    path: "/usr/local/bin/glomap"  # 修改为实际路径

image_roots:
  default: "/path/to/your/images"  # 修改为图像存储路径
```

**可选：配置通知服务**：
```bash
cp observability.yaml.example observability.yaml
vim observability.yaml  # 编辑通知配置
```

### 5. 初始化数据库

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 数据库会在首次启动时自动创建
```

---

## 前端安装

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置API地址

编辑 `src/api/index.ts`，确保 `BASE_URL` 指向后端地址：

```typescript
export const BASE_URL = 'http://localhost:8000';
```

### 3. 启动开发服务器

```bash
npm run dev -- --host 0.0.0.0 --port 3000
```

访问 http://localhost:3000

---

## 算法安装

AeroTri-Web 依赖外部算法库，需要单独安装。

### COLMAP（推荐）

**从源码编译**：

```bash
git clone https://github.com/colmap/colmap.git
cd colmap
mkdir build && cd build
cmake .. -DCMAKE_CUDA_ARCHITECTURES=native
make -j$(nproc)
sudo make install
```

**预编译版本**：
- Ubuntu: `sudo apt-get install colmap`
- macOS: `brew install colmap`

### GLOMAP

```bash
git clone https://github.com/APRIL-ZJU/GLoMAP.git
cd GLoMAP
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

### OpenMVG

```bash
git clone https://github.com/openMVG/openMVG.git
cd openMVG
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RELEASE
make -j$(nproc)
```

### InstantSfM

```bash
git clone https://github.com/zju3dv/instant-sfm.git
cd instant-sfm
# 按照官方文档安装
```

### OpenMVS

**Ubuntu（预编译）**：
```bash
sudo apt-add-repository ppa:cdcseacave/openmvs
sudo apt-get update
sudo apt-get install openmvs
```

**从源码编译**：
```bash
git clone https://github.com/cdcseacave/openMVS.git
cd openMVS
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RELEASE
make -j$(nproc)
sudo make install
```

### 3D Gaussian Splatting

```bash
git clone --recursive https://github.com/nerfstudio-project/gaussian-splatting.git
cd gaussian-splatting
pip install -r requirements.txt
```

---

## 配置

### 环境变量配置（可选）

创建 `.env` 文件或设置环境变量：

```bash
# 数据库
export AEROTRI_DB_PATH=/var/lib/aerotri/aerotri.db

# 图像根路径
export AEROTRI_IMAGE_ROOTS=/data/images:/mnt/storage

# 算法路径
export COLMAP_PATH=/usr/local/bin/colmap
export GLOMAP_PATH=/usr/local/bin/glomap
export INSTANTSFM_PATH=/usr/local/bin/ins-sfm
export GS_REPO_PATH=/opt/gaussian-splatting
export GS_PYTHON=/opt/gs_env/bin/python

# GPU配置
export CUDA_VISIBLE_DEVICES=0

# 队列配置
export QUEUE_MAX_CONCURRENT=2
```

---

## 验证安装

### 1. 检查后端

```bash
curl http://localhost:8000/api/system/status
```

应返回系统状态信息。

### 2. 检查算法

```bash
colmap --version
glomap --version
ins-sfm --help
```

所有命令应显示版本信息。

### 3. 检查前端

访问 http://localhost:3000，应显示Web界面。

### 4. 运行测试

**后端测试**：
```bash
cd backend
pytest
```

**前端测试**：
```bash
cd frontend
npm run test
```

---

## 故障排查

### 后端无法启动

**问题**: 端口被占用
```bash
# 检查端口占用
lsof -i :8000
# 或使用其他端口
uvicorn app.main:app --port 8001
```

**问题**: 数据库权限错误
```bash
chmod 755 backend/data
```

**问题**: 算法路径不正确
```bash
# 检查算法是否在PATH中
which colmap
# 或使用绝对路径
```

### 前端无法连接后端

**问题**: CORS错误
```yaml
# 检查 backend/config/application.yaml
app:
  cors_origins:
    - "http://localhost:3000"
```

**问题**: 代理配置错误
```javascript
// 检查 frontend/vite.config.mjs
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

### GPU不被识别

**问题**: CUDA未安装
```bash
nvidia-smi  # 检查NVIDIA驱动
nvcc --version  # 检查CUDA编译器
```

**问题**: PyTorch CUDA版本不匹配
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 算法执行失败

**问题**: COLMAP特征提取失败
- 检查图像格式是否支持（JPG、PNG）
- 检查EXIF信息是否存在
- 尝试降低 `max_image_size`

**问题**: 内存不足
- 减少并行任务数（`QUEUE_MAX_CONCURRENT`）
- 使用分区模式处理大数据集
- 增加交换空间

---

## 生产部署

### 使用 systemd

创建 `/etc/systemd/system/aerotri-backend.service`：

```ini
[Unit]
Description=AeroTri Backend
After=network.target

[Service]
User=aerotri
WorkingDirectory=/opt/Aerotri-Web/aerotri-web/backend
Environment="PATH=/opt/Aerotri-Web/aerotri-web/backend/venv/bin"
ExecStart=/opt/Aerotri-Web/aerotri-web/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable aerotri-backend
sudo systemctl start aerotri-backend
```

### 使用 Docker

详见 `docker-compose.yml`。

```bash
docker-compose up -d
```

---

## 下一步

安装完成后，请参考：
- [快速开始](./01-quickstart/) - 第一个重建任务
- [用户指南](./03-user-guide/) - 功能详细说明
- [算法文档](./04-algorithms/) - 算法参数配置
