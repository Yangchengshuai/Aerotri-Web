# 前端测试 GLOMAP Pose Prior 功能

## 前置条件

1. **后端已启动**：
   ```bash
   cd /root/work/aerotri-web/backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **GLOMAP 可执行文件已编译**：
   - 路径：`/root/work/colmap/build_poseprior_ceres23_cudss_nocgal/src/glomap/glomap`
   - 已包含 pose prior 功能（`--PosePrior.use_prior_position`）

3. **前端已编译**：
   ```bash
   cd /root/work/aerotri-web/frontend
   npm install
   npm run dev  # 开发模式
   # 或使用已编译的 dist/ 目录
   ```

## 测试步骤

### 1. 启动前端开发服务器

```bash
cd /root/work/aerotri-web/frontend
npm run dev
```

访问 http://localhost:3000

### 2. 创建新的 Block

1. 点击"创建 Block"
2. 选择图像目录（确保包含 `database.db` 且 `pose_priors` 表有数据）
3. 选择算法：**GLOMAP (全局式)**

### 3. 配置 Pose Prior

在参数配置页面：

1. 展开 **"Mapper 参数"** 部分
2. 找到 **"启用位置先验"** 开关
3. **开启** 该开关
4. 查看提示信息：`显式传入 --PosePrior.use_prior_position 1`

### 4. 运行任务

1. 保存参数配置
2. 点击"运行"按钮
3. 观察日志输出，确认：
   - `[CMD]` 日志显示完整的 CLI 命令
   - 命令中包含 `--PosePrior.use_prior_position 1`
   - GLOMAP 日志显示：
     - `Converted X pose prior positions WGS84->UTM`
     - `Initialized X frame translations from position priors`
     - `PosePrior: extracted X frame position priors`
     - `PosePriorBundleAdjuster: added X position prior constraints`

### 5. 验证结果

1. 等待任务完成
2. 查看 3D 可视化：
   - 相机和点云应该在正确的 UTM 坐标范围内（不是归一化的 ~1 范围）
   - 相机位置应该与 GPS/RTK 数据对齐
3. 查看日志文件 `run.log`：
   - 搜索 `[DIAG][GP]` 和 `[DIAG][BA]` 日志
   - 确认坐标范围从归一化（~1）正确转换回 UTM（米制）

## 预期行为

### 启用 Pose Prior 时

- **CLI 命令**：包含 `--PosePrior.use_prior_position 1`
- **GP 阶段**：使用 position priors 初始化 frame translations
- **BA 阶段**：使用 `PosePriorBundleAdjuster`，添加 position prior constraints
- **输出坐标**：UTM 米制坐标（不是归一化坐标）

### 未启用 Pose Prior 时

- **CLI 命令**：不包含 `--PosePrior.use_prior_position`
- **GP 阶段**：随机初始化位置
- **BA 阶段**：使用标准 `BundleAdjuster`
- **输出坐标**：归一化坐标（需要后续对齐）

## 故障排查

### 问题：前端开关不显示

- 检查 `ParameterForm.vue` 中 `formData.algorithm === 'glomap'` 条件
- 确认 `mapper_params.pose_prior_use_prior_position` 字段存在

### 问题：后端未传递 CLI 参数

- 检查 `task_runner.py` 中 `_run_glomap_mapper` 方法
- 确认 `params.get("pose_prior_use_prior_position", False)` 逻辑正确
- 查看 `[CMD]` 日志确认命令构建正确

### 问题：GLOMAP 报错或输出归一化坐标

- 检查 `database.db` 中 `pose_priors` 表是否有数据
- 检查 `position_covariance` 是否为 `NaN`（会自动 fallback 到默认值）
- 查看 `run.log` 中的 `[DIAG]` 日志定位问题

## 环境变量配置

如果需要使用不同的 GLOMAP 可执行文件：

```bash
export GLOMAP_PATH=/path/to/your/glomap
```

或在 `task_runner.py` 中修改默认值。

