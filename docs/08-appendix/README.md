# 08-appendix

AeroTri-Web 附录文档，提供术语表、常见问题和参考资源。

## 目录

- [术语表](#术语表)
- [常见问题](#常见问题)
- [错误代码](#错误代码)
- [参考资源](#参考资源)

---

## 术语表

### 核心概念

| 术语 | 英文 | 说明 |
|------|------|------|
| **Block** | Block | 摄影测量工作单元，表示图像集合和相关的重建任务 |
| **SfM** | Structure from Motion | 从图像序列中恢复相机姿态和稀疏点云的过程 |
| **重建版本** | Reconstruction Version | Block的多个重建结果，每个版本独立配置参数 |
| **3DGS** | 3D Gaussian Splatting | 3D高斯溅射，实时渲染的3D场景表示方法 |
| **3D Tiles** | 3D Tiles | 三维瓦片格式，用于大规模3D地理数据流传输和渲染 |

### 算法术语

| 术语 | 说明 |
|------|------|
| **COLMAP** | Incremental SfM | 增量式SfM，逐步注册和优化图像 |
| **GLOMAP** | Global SfM | 全局式SfM，通过全局优化快速恢复相机姿态 |
| **InstantSfM** | Instant SfM | 快速全局SfM，支持实时3D可视化 |
| **OpenMVG** | OpenMVG | 开源多视图几何库，CPU友好的SfM实现 |
| **OpenMVS** | OpenMVS | 开源多视图立体重建库，生成密集点云和网格 |

### 技术术语

| 术语 | 说明 |
|------|------|
| **特征提取** | Feature Extraction | 从图像中检测和描述局部特征点（如SIFT、SURF）的过程 |
| **特征匹配** | Feature Matching | 在不同图像间匹配对应的特征点，建立图像间对应关系 |
| **Bundle Adjustment** | BA | 联合优化所有相机参数和3D点，最小化重投影误差 |
| **密集重建** | Dense Reconstruction | 从稀疏点云生成密集点云的过程 |
| **GPU Prior** | GPS Prior | 使用GPS先验信息约束SfM优化 |
| **分区** | Partition | 将大数据集分成多个子集分别处理，最后合并结果 |
| **WebSocket** | WebSocket | 全双工通信协议，支持实时双向通信 |
| **稀疏点云** | Sparse Point Cloud | SfM输出的3D点集，点数相对较少但精度高 |
| **密集点云** | Dense Point Cloud | 密集重建输出的3D点集，点数密集 |
| **地理参考** | Georeferencing | 将3D模型从局部坐标系转换到地理坐标系（如UTM/WGS84） |

### 状态术语

| 状态 | 说明 |
|------|------|
| **created** | 已创建 | Block已创建但尚未启动 |
| **queued** | 队列中 | Block在队列中等待执行 |
| **running** | 正在处理 | 任务正在执行 |
| **completed** | 处理完成 | 任务成功完成 |
| **failed** | 处理失败 | 任务执行失败 |
| **cancelled** | 已取消 | 任务被用户取消 |

---

## 常见问题

### 安装和配置

**Q: Docker启动失败？**
A: 检查Docker和Docker Compose版本
```bash
docker --version
docker-compose --version
```

**Q: 后端无法启动，报错"数据库被锁定"？**
A: SQLite数据库被其他进程占用
```bash
# 检查并终止占用进程
lsof | grep aerotri.db
fuser aerotri.db
```

**Q: GPU监控不工作？**
A: PyNvml未安装或NVIDIA驱动未安装
```bash
# 检查NVIDIA驱动
nvidia-smi

# 安装PyNvml
pip install nvidia-ml-py3
```

**Q: 前端无法连接后端CORS错误？**
A: 检查CORS配置
```yaml
# backend/config/defaults.yaml
cors_origins:
  - "http://localhost:3000"  # 确保端口正确
```

**Q: 算法路径不正确？**
A: 使用绝对路径或确保在PATH中
```bash
# 检查算法是否在PATH中
which colmap
which glomap

# 如果不在PATH，使用绝对路径
export COLMAP_PATH=/usr/local/bin/colmap
```

### 任务执行问题

**Q: SfM任务一直在"running"状态？**
A: 检查后端日志，可能subprocess进程未正常终止
```bash
# 查看后端日志
tail -f aerotri-web/backend/logs/app.log

# 检查是否有僵尸进程
ps aux | grep colmap
```

**Q: 任务失败后如何重试？**
A: 在Block详情页点击"重置"后重新运行
```bash
# 或使用API
curl -X POST http://localhost:8000/api/blocks/{block_id}/reset
```

**Q: 如何取消正在运行的任务？**
A: 在Block详情页点击"取消"按钮
或在队列中点击"取消"

**Q: 重建版本可以删除吗？**
A: 可以，但只能删除非运行状态的版本

### 3D Gaussian Splatting

**Q: 3DGS训练很慢怎么办？**
A:
1. 降低分辨率（`resolution: 2`）
2. 减少迭代次数（`iterations: 10000`）
3. 减少`densify_until_iter`
4. 使用更好的GPU

**Q: 3DGS需要什么相机模型？**
A: 必须是PINHOLE或SIMPLE_PINHOLE
- 系统会自动运行undistortion转换其他模型
- 或在前端手动选择相机模型

**Q: 如何导出SPZ压缩格式？**
A: 在训练参数中启用
```yaml
gs_params:
  export_spz: true
```

**Q: SPZ压缩比是多少？**
A: 约90%压缩比
- 原始PLY: ~180MB
- 压缩后SPZ: ~15MB

### 3D Tiles转换

**Q: 什么是3D Tiles？**
A: OGC（Open Geospatial Consortium）标准的三维瓦片格式
- 用于大规模3D地理数据流传输和渲染
- 支持LOD（Level of Detail）多级细节层次
- Cesium原生支持

**Q: OpenMVS和3DGS的3D Tiles有什么区别？**
A:
- **OpenMVS Tiles**: 基于OBJ/GLB模型的静态瓦片
- **3DGS Tiles**: 基于高斯点云的动态瓦片，支持SPZ压缩
- 文件格式和结构不同

**Q: 如何在Cesium中查看3D Tiles？**
A:
1. 在Block详情页点击"在Cesium中查看"
2. 或直接访问tileset.json
```javascript
const viewer = new Cesium.Viewer('cesiumContainer')
const tileset = await Cesium.Cesium3DTileset.fromUrl('http://localhost:8000/tiles/tileset.json')
viewer.scene.primitives.add(tileset)
```

### 性能优化

**Q: 大数据集处理慢？**
A: 使用分区模式
```yaml
# 启用分区
enable_partition: true
partition_size: 500  # 每分区500张图像
```

**Q: 内存不足错误？**
A:
1. 减少并发任务数（`QUEUE_MAX_CONCURRENT: 1`）
2. 降低图像分辨率
3. 使用更低的特征数量

**Q: GPU显存不足？**
A:
1. 减少同时运行的任务
2. 监控GPU使用情况
3. 选择显存较多的GPU

---

## 错误代码

### 任务执行错误

| 错误代码 | 说明 | 解决方案 |
|---------|------|----------|
| `E001` | 图像路径不存在 | 检查图像路径是否正确 |
| `E002` | 算法可执行文件不存在 | 安装对应算法并添加到PATH |
| `E003` | 图像格式不支持 | 转换图像为JPG/PNG格式 |
| `E004` | GPU初始化失败 | 检查CUDA和NVIDIA驱动安装 |
| `E005` | 任务超时 | 增加任务超时时间或优化算法参数 |
| `E006` | 磁盘空间不足 | 清理输出目录或使用外部存储 |
| `E007` | 内存不足 | 关闭其他应用或增加系统内存 |

### 数据库错误

| 错误代码 | 说明 | 解决方案 |
|---------|------|----------|
| `D001` | 数据库文件被锁定 | 检查是否有其他后端实例在运行 |
| `D002` | 数据库磁盘空间不足 | 清理系统空间或移动到更大的磁盘 |
| `D003` | 数据库连接失败 | 检查数据库路径配置和权限 |

### API错误

| 错误代码 | HTTP状态 | 说明 | 解决方案 |
|---------|----------|----------|
| `A001` | 400 Bad Request | 请求参数不正确，检查API文档 |
| `A002` | 401 Unauthorized | 未授权访问，检查登录状态 |
| `A003` | 403 Forbidden | 权限不足，检查用户权限 |
| `A004` | 404 Not Found | 资源不存在，检查URL是否正确 |
| `A005` | 409 Conflict | 资源冲突，检查是否有重复操作 |
| `A006` | 422 Unprocessable Entity | 请求格式错误，检查请求数据 |
| `A007` | 429 Too Many Requests | 请求过于频繁，稍后重试 |
| `A008` | 500 Internal Server Error | 服务器内部错误，查看后端日志 |
| `A009` | 503 Service Unavailable | 服务暂时不可用，稍后重试 |

### WebSocket错误

| 错误代码 | 说明 | 解决方案 |
|---------|------|----------|
| `W001` | 连接失败 | 检查后端WebSocket服务是否运行 |
| `W002` | 订阅失败 | Block ID可能不正确 |
| `W003` | 消息格式错误 | 检查消息格式是否符合要求 |
| `W004` | 心跳超时 | 网络不稳定，检查网络连接 |
| `W005` | 连接关闭 | 客户端主动断开或网络中断 |

---

## 参考资源

### 官方文档

**算法文档**：
- [COLMAP](https://colmap.github.io/) - 增量SfM
- [GLOMAP](https://github.com/APRIL-ZJU/GLoMAP) - 全局SfM
- [InstantSfM](https://github.com/zju3dv/instant-sfm) - 快速SfM
- [OpenMVG](https://github.com/openMVG/openMVG) - 多视图几何
- [OpenMVS](https://github.com/cdcseacave/openMVS) - 密集重建

**3D Gaussian Splatting**：
- [3DGS](https://github.com/nerfstudio-project/gaussian-splatting) - 原始论文和实现
- [gaussian-splatting-demo](https://github.com/GraphLearn/gaussian-splatting-demo) - 演示和测试

**3D Tiles**：
- [3D Tiles Specification](https://www.ogc.org/3dtiles/) - OGC 3D Tiles规范
- [CesiumJS Documentation](https://cesium.com/learn) - Cesium前端库
- [CesiumGS](https://github.com/CesiumGS) - Cesium工具集

### 开发框架

**后端框架**：
- [FastAPI](https://fastapi.tiangolo.com/) - 现代高性能Web框架
- [SQLAlchemy](https://docs.sqlalchemy.org/) - Python SQL工具包和ORM
- [Pydantic](https://docs.pydantic.dev/) - 数据验证和设置
- [Uvicorn](https://www.uvicorn.org/) - ASGI服务器

**前端框架**：
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Pinia](https://pinia.vuejs.org/) - Vue状态管理
- [Element Plus](https://element-plus.org/) - Vue组件库
- [Three.js](https://threejs.org/) - 3D图形库
- [Cesium](https://cesium.com/learn) - 3D地球和地图可视化
- [Vite](https://vitejs.dev/) - 下一代前端构建工具

### 工具和库

**Python库**：
- [PyTorch](https://pytorch.org/) - 深度学习框架
- [NumPy](https://numpy.org/) - 科学计算
- [OpenCV](https://opencv.org/) - 计算机视觉
- [PyProj](https://pyproj4.org/) - 地理坐标转换

**测试工具**：
- [Pytest](https://docs.pytest.org/) - Python测试框架
- [Vitest](https://vitest.dev/) - 单元测试框架
- [ESLint](https://eslint.org/) - JavaScript/TypeScript代码检查
- [Black](https://black.readthedocs.io/) - Python代码格式化

### 社区资源

- [Stack Overflow](https://stackoverflow.com/) - 技术问答
- [GitHub](https://github.com/) - 代码托管和协作
- [Reddit](https://www.reddit.com/r/photogrammetry/) - 摄影测量社区

### 学习资源

**在线课程**：
- [Photogrammetry I](https://www.e-education.net/Photogrammetry-I/) - 摄影测量基础I
- [Photogrammetry II](https://www.e-education.net/Photogrammetry-II/) - 摄影测量进阶
- [Computer Vision](https://www.coursera.org/learn/computer-vision) - 计算机视觉

**书籍推荐**：
- *Multiple View Geometry in Computer Vision* - Hartley & Zisserman
- *Computer Vision: Algorithms and Applications* - Szeliski et al.
- *An Invitation to 3D Computer Vision* - F. P.iasco & M. Brady

---

## 附录更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2024-02-12 | v1.0.0 | 初始版本 |
| 2024-11-20 | v1.0.0 | 补充安装、用户指南和算法文档 |
| 2024-11-20 | v1.0.0 | 补充开发指南和贡献指南 |
| 2024-11-20 | v1.0.0 | 补充附录文档，完成文档体系 |

---

## 使用提示

### 如何使用此附录

1. **遇到问题**：先查阅[常见问题](#常见问题)和[错误代码](#错误代码)
2. **学习新算法**：参考[算法文档](../04-algorithms/)和[官方文档](#官方文档)
3. **贡献代码**：遵循[贡献指南](../07-contribution/)中的规范
4. **扩展功能**：参考[开发指南](../05-development/)中的架构说明

### 快速查找

- **查找术语**：使用浏览器搜索（Ctrl+F）查找关键词
- **返回目录**：点击目录中的链接快速跳转
- **查看参考**：所有外部链接都在新标签页打开

---

感谢使用AeroTri-Web！
