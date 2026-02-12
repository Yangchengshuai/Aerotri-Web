# 03-user-guide

AeroTri-Web 用户指南，详细说明如何使用系统进行摄影测量处理。

## 目录

- [核心概念](#核心概念)
- [界面概览](#界面概览)
- [Block管理](#block管理)
- [SfM重建](#sfm重建)
- [密集重建](#密集重建)
- [3D Gaussian Splatting](#3d-gaussian-splatting)
- [3D Tiles转换](#3d-tiles转换)
- [GPU监控](#gpu监控)
- [任务队列](#任务队列)

---

## 核心概念

### Block（区块）

Block 是 AeroTri-Web 中的核心工作单元，代表一个图像集合和相关的重建任务。

**Block 包含的信息**：
- 图像路径和工作目录
- 算法选择和参数配置
- 任务状态和进度
- 重建结果和统计信息

### SfM（Structure from Motion）

SfM 是从图像序列中恢复相机姿态和稀疏点云的过程。

**支持的算法**：
- **COLMAP**: 增量式 SfM，适合常规场景
- **GLOMAP**: 全局 SfM，适合大规模场景
- **InstantSfM**: 快速 SfM，实时可视化
- **OpenMVG**: CPU 友好，无 GPU 环境

### 重建版本（Reconstruction Version）

每个 Block 可以有多个重建版本，每个版本独立配置参数。

**用途**：
- 对比不同参数的效果
- 尝试不同的质量设置
- 保留多个结果供选择

---

## 界面概览

### 主界面

访问 http://localhost:3000 后，您将看到：

1. **顶部导航栏**
   - Block 列表
   - GPU 状态
   - 队列管理

2. **Block 卡片列表**
   - 显示所有 Block
   - 状态标签（进行中/已完成/失败）
   - 快速操作按钮

3. **侧边栏**（选择 Block 后）
   - Block 详情
   - 参数配置
   - 进度监控

---

## Block管理

### 创建 Block

1. 点击右上角 **"创建 Block"** 按钮

2. 填写基本信息：
   - **名称**: Block 的描述性名称
   - **图像路径**: 图像所在目录
   - **算法**: 选择 SfM 算法（默认 GLOMAP）

3. 配置参数（可选）：
   - **特征提取**: 相机模型、最大特征数等
   - **特征匹配**: 匹配方法、重叠度等
   - **Mapper**: 稠密重建、最小图像数等

4. 点击 **"创建"**

### Block 状态

| 状态 | 说明 |
|------|------|
| `pending` | 等待运行 |
| `running` | 正在处理 |
| `completed` | 处理完成 |
| `failed` | 处理失败 |
| `cancelled` | 已取消 |

### Block 操作

**查看详情**：点击 Block 卡片

**删除 Block**：
- 只能删除非运行状态的 Block
- 删除会移除所有相关数据

**取消任务**：点击"取消"按钮停止运行中的任务

**导出结果**：使用导出按钮下载重建结果

---

## SfM重建

### 选择算法

#### COLMAP（推荐新手）

**优点**：
- 稳定可靠
- 支持多种相机模型
- 有 GPS prior 支持

**适用场景**：
- 常规航空摄影
- 地面拍摄
- 有 GPS 信息的图像

**关键参数**：
```yaml
feature_params:
  camera_model: "SIMPLE_PINHOLE"  # 简单针孔模型
  max_num_features: 8192         # 特征点数量

matching_params:
  method: "sequential"            # 顺序匹配
  overlap: 10                     # 重叠度

mapper_params:
  min_num_matches: 15            # 最小匹配点数
  mapper: "sequential"            # 增量式重建
```

#### GLOMAP（推荐大规模数据）

**优点**：
- 全局优化
- 速度快
- 可迭代优化

**适用场景**：
- 大规模航拍（1000+ 图像）
- 需要快速处理

**关键参数**：
```yaml
glomap_params:
  mode: "mapping"                # mapping 或 mapper_resume
  estimate_refine: true          # 估计并细化
```

#### InstantSfM（推荐实时可视化）

**优点**：
- 实时 3D 可视化
- 处理速度快
- 支持交互

**适用场景**：
- 需要实时查看结果
- 快速原型验证

#### OpenMVG（推荐 CPU 环境）

**优点**：
- 纯 CPU 运行
- 内存占用低
- 线程自适应

**适用场景**：
- 无 GPU 环境
- 内存受限

**关键参数**：
```yaml
openmvg_params:
  num_threads: "auto"            # 自动线程数
  desc_type: "SIFT"              # 描述子类型
```

### 配置参数

#### 特征提取参数

| 参数 | 说明 | 默认值 | 建议 |
|------|------|--------|------|
| `camera_model` | 相机模型 | SIMPLE_PINHOLE | 3DGS 需要 PINHOLE |
| `max_image_size` | 最大图像尺寸 | 2048 | 高分辨率可增大 |
| `max_num_features` | 最大特征数 | 8192 | 复杂场景可增大 |
| `single_camera` | 单相机假设 | true | 航拍通常为 true |

#### 特征匹配参数

| 参数 | 说明 | 默认值 | 建议 |
|------|------|--------|------|
| `method` | 匹配方法 | sequential | 大数据用 spatial |
| `overlap` | 顺序匹配重叠度 | 10 | 60-70% 重叠设 10-20 |
| `spatial_max_num_neighbors` | 空间匹配邻居数 | 20 | 密集采集可增大 |

#### Mapper 参数

| 参数 | 说明 | 默认值 | 建议 |
|------|------|--------|------|
| `min_num_matches` | 最小匹配点数 | 15 | 提高可减少误匹配 |
| `mapper` | 重建策略 | incremental | 大数据用 global |
| `refine_extra_params` | 额外优化参数 | true | GPS 场景启用 |

### 启动重建

1. 在 Block 详情页，点击 **"开始重建"**

2. 选择运行方式：
   - **立即运行**: 直接启动
   - **加入队列**: 添加到任务队列

3. 选择 GPU（可选）：
   - 查看实时 GPU 状态
   - 选择最空闲的 GPU

4. 点击 **"确认"**

### 监控进度

**实时进度显示**：
- 当前阶段
- 进度百分比
- 剩余时间估算
- 日志输出

**SfM 处理阶段**：
1. `importing` - 导入图像
2. `feature_extraction` - 特征提取
3. `feature_matching` - 特征匹配
4. `mapping` - 稀疏重建
5. `completed` - 完成

---

## 密集重建

### 创建重建版本

1. 在已完成 SfM 的 Block 中，点击 **"密集重建"**

2. 选择质量预设：
   - **Low**: 快速预览
   - **Medium**: 平衡质量和速度（推荐）
   - **High**: 最高质量

3. 配置参数（可选）：
   - 密集点云分辨率
   - 网格重构方法
   - 纹理映射质量

4. 点击 **"开始重建"**

### OpenMVS 处理阶段

1. `densifying` - 密集点云生成
2. `meshing` - 网格重构
3. `refining` - 网格优化
4. `texturing` - 纹理映射
5. `completed` - 完成

### 版本管理

**查看所有版本**：
- 在 Block 详情页切换到"重建版本"标签

**版本对比**：
- 选择两个版本进行并排对比
- 使用分割滑块对比 3D 效果

**删除版本**：
- 删除不需要的版本释放存储空间

---

## 3D Gaussian Splatting

### 准备工作

**必需条件**：
- SfM 已完成
- 相机模型为 PINHOLE 或 SIMPLE_PINHOLE
- 系统会自动运行 undistortion（如需要）

### 启动训练

1. 在 Block 详情页，点击 **"3DGS 训练"**

2. 配置训练参数：
   ```yaml
   gs_params:
     iterations: 30000              # 迭代次数
     resolution: 1                  # 分辨率缩放
     eval: false                     # 评估
     OpacityReset: "7000"           # 不透明度重置间隔
     DensifyUntilIter: 15000       # 密集化迭代数
   ```

3. 选择输出选项：
   - 导出 SPZ 压缩格式（减少 90% 文件大小）
   - 启动 TensorBoard 可视化

4. 点击 **"开始训练"**

### 训练监控

**实时指标**：
- 当前迭代数
- 损失值（Loss）
- PSNR 和 SSIM
- 点云数量
- GPU 内存使用

**TensorBoard**：
```bash
# 访问 TensorBoard
http://localhost:6006
```

### 输出结果

**训练完成后**：
- `point_cloud/iteration_*/` - 迭代检查点
- `point_cloud.ply` - 最终点云
- `point_cloud.spz` - 压缩点云（可选）
- `train/` - 训练日志

---

## 3D Tiles转换

### OpenMVS → 3D Tiles

1. 在重建版本中，点击 **"转换为 3D Tiles"**

2. 配置转换参数：
   - 地理定位（需要 GPS）
   - 几何误差阈值

3. 点击 **"开始转换"**

### 3DGS → 3D Tiles

1. 在 3DGS 训练完成后，点击 **"转换为 3D Tiles"**

2. 配置选项：
   - 使用 SPZ 压缩（推荐）
   - 纹理质量

3. 点击 **"开始转换"**

### 查看 3D Tiles

**使用 Cesium 查看器**：
1. 在 Block 详情页，点击 **"在 Cesium 中查看"**
2. 拖拽、旋转、缩放查看 3D 模型
3. 使用分割视图对比版本

---

## GPU监控

### 实时监控

**GPU 状态面板**显示：
- GPU 编号和型号
- 显存使用率
- GPU 使用率
- 温度
- 正在运行的任务

### GPU 选择建议

**选择策略**：
- **最空闲**: 选择显存最多的 GPU
- **自动分配**: 系统自动选择
- **手动指定**: 指定 GPU 编号

**注意事项**：
- 3DGS 训练需要较大显存（建议 8GB+）
- SfM 特征提取可以共享 GPU
- 避免在同一个 GPU 上运行过多任务

---

## 任务队列

### 添加到队列

1. 创建 Block 后，选择 **"加入队列"**
2. 任务会在资源可用时自动启动

### 队列配置

**并发控制**：
```yaml
queue:
  max_concurrent: 2  # 最多同时运行 2 个任务
```

**调整并发数**：
- 低配置机器：1
- 高性能机器：2-4
- GPU 数量：建议 ≤ GPU 数量

### 队列管理

**查看队列**：
- 在导航栏点击 **"队列"**
- 查看等待中和运行中的任务

**取消排队**：
- 点击"取消"移除等待中的任务

**调整顺序**：
- 点击"上移"/"下移"调整优先级

---

## 常见问题

### Q: 为什么重建失败？

**检查清单**：
1. 图像是否有足够的重叠度（建议 60-70%）
2. EXIF 信息是否存在（GPS、焦距）
3. 内存是否充足（建议 32GB+）
4. GPU 驱动是否正常

**查看错误日志**：
- 在 Block 详情页查看完整日志
- 搜索"Error"、"Failed"关键字

### Q: 如何提高重建质量？

**建议**：
1. 增加图像数量和重叠度
2. 提高图像分辨率
3. 启用 GPS prior
4. 使用更高质量预设
5. 调整特征提取参数

### Q: 大数据集如何处理？

**使用分区模式**：
1. 启用"分区处理"
2. 设置合理的分区大小
3. 系统会自动合并结果

### Q: 3DGS 训练很慢怎么办？

**优化建议**：
1. 降低分辨率
2. 减少迭代次数
3. 使用更好的 GPU
4. 减少 Dense Until Iteration

---

## 最佳实践

1. **图像采集**
   - 保持 60-70% 重叠度
   - 避免运动模糊
   - 包含足够的几何变化

2. **参数选择**
   - 新手使用默认参数
   - 大数据集用 GLOMAP
   - 需要实时性用 InstantSfM

3. **资源管理**
   - 监控 GPU 使用率
   - 合理设置并发任务数
   - 及时清理不需要的数据

4. **结果验证**
   - 检查重投影误差
   - 查看相机轨迹
   - 对比多个版本

---

## 下一步

- [算法文档](./04-algorithms/) - 算法详细说明
- [开发指南](./05-development/) - API 和扩展
- [AI 协作](./06-ai-collaboration/) - AI 辅助开发
