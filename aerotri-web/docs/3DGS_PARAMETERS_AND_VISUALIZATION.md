# 3DGS 参数扩展与训练可视化功能分析

## 一、当前参数实现情况

### 前端已实现参数（4个）
根据界面截图和代码，当前前端支持：
1. **iterations** (iters): 7000 - 训练迭代次数
2. **resolution** (res): 2 - 分辨率缩放
3. **data_device**: cpu/cuda - 数据设备
4. **sh_degree** (sh): 3 - 球谐函数度数

### 后端传递情况
后端 `gs_runner.py` 仅传递了这4个参数到训练脚本。

---

## 二、建议扩展的参数（按优先级）

### 🔴 高优先级（常用且重要）

#### 1. **test_iterations** - 测试迭代点
- **作用**：在指定迭代次数进行测试评估（计算PSNR/SSIM等指标）
- **默认值**：`[7000, 30000]`
- **类型**：整数数组
- **建议UI**：多选输入框或逗号分隔输入
- **重要性**：⭐⭐⭐⭐⭐ 用于评估训练质量

#### 2. **save_iterations** - 保存迭代点
- **作用**：在指定迭代次数保存模型checkpoint
- **默认值**：`[7000, 30000]`
- **类型**：整数数组
- **建议UI**：多选输入框或逗号分隔输入
- **重要性**：⭐⭐⭐⭐⭐ 用于保存中间结果

#### 3. **white_background** - 白色背景
- **作用**：使用白色背景而非黑色背景（影响渲染效果）
- **默认值**：`False`
- **类型**：布尔值
- **建议UI**：开关/复选框
- **重要性**：⭐⭐⭐⭐ 影响最终渲染效果

#### 4. **quiet** - 安静模式
- **作用**：减少控制台输出
- **默认值**：`False`
- **类型**：布尔值
- **建议UI**：开关（可选，默认关闭）
- **重要性**：⭐⭐⭐ 减少日志噪音

#### 5. **disable_viewer** - 禁用实时查看器
- **作用**：禁用network_gui实时可视化（节省资源）
- **默认值**：`False`
- **类型**：布尔值
- **建议UI**：开关（默认关闭，启用实时可视化）
- **重要性**：⭐⭐⭐ 影响训练可视化

### 🟡 中优先级（高级用户需要）

#### 6. **densify_from_iter** - 开始密集化迭代
- **作用**：从哪个迭代开始密集化（添加新Gaussians）
- **默认值**：`500`
- **类型**：整数
- **重要性**：⭐⭐⭐ 影响训练质量

#### 7. **densify_until_iter** - 停止密集化迭代
- **作用**：到哪个迭代停止密集化
- **默认值**：`15000`
- **类型**：整数
- **重要性**：⭐⭐⭐ 影响训练质量

#### 8. **densification_interval** - 密集化间隔
- **作用**：每隔多少迭代进行一次密集化
- **默认值**：`100`
- **类型**：整数
- **重要性**：⭐⭐ 影响训练效率

#### 9. **lambda_dssim** - DSSIM损失权重
- **作用**：DSSIM损失在总损失中的权重
- **默认值**：`0.2`
- **类型**：浮点数
- **重要性**：⭐⭐ 影响训练质量

#### 10. **opacity_reset_interval** - 不透明度重置间隔
- **作用**：每隔多少迭代重置不透明度
- **默认值**：`3000`
- **类型**：整数
- **重要性**：⭐⭐ 影响训练稳定性

### 🟢 低优先级（专家级参数）

#### 学习率参数
- `position_lr_init`: 位置学习率初始值 (默认: 0.00016)
- `position_lr_final`: 位置学习率最终值 (默认: 0.0000016)
- `feature_lr`: 特征学习率 (默认: 0.0025)
- `opacity_lr`: 不透明度学习率 (默认: 0.025)
- `scaling_lr`: 缩放学习率 (默认: 0.005)
- `rotation_lr`: 旋转学习率 (默认: 0.001)

#### 其他优化参数
- `percent_dense`: 密集化百分比 (默认: 0.01)
- `densify_grad_threshold`: 密集化梯度阈值 (默认: 0.0002)
- `depth_l1_weight_init`: 深度L1损失初始权重 (默认: 1.0)
- `depth_l1_weight_final`: 深度L1损失最终权重 (默认: 0.01)

#### 渲染管道参数
- `antialiasing`: 抗锯齿 (默认: False)
- `convert_SHs_python`: Python SH转换 (默认: False)
- `compute_cov3D_python`: Python协方差计算 (默认: False)

---

## 三、训练可视化功能

### 3.1 TensorBoard 可视化

#### 当前状态
- ✅ 3DGS训练脚本已集成TensorBoard支持
- ✅ 如果安装了tensorboard，会自动记录训练指标
- ❌ 前端没有TensorBoard集成

#### 记录的指标
根据 `train.py` 代码，TensorBoard会记录：
1. **训练损失**：
   - `train_loss_patches/l1_loss` - L1损失
   - `train_loss_patches/total_loss` - 总损失
   - `train_loss_patches/iter_time` - 迭代时间

2. **测试指标**（在test_iterations时）：
   - `test/psnr` - PSNR值
   - `test/ssim` - SSIM值
   - `test/lpips` - LPIPS值（如果可用）

3. **场景统计**：
   - `scene/opacity_histogram` - 不透明度直方图
   - `total_points` - 总点数

#### 实现建议

**方案1：集成TensorBoard Web UI**
```python
# 后端：启动TensorBoard服务器
# 前端：iframe嵌入TensorBoard Web UI
```

**方案2：自定义指标图表**
- 从TensorBoard日志文件读取数据
- 使用前端图表库（如Chart.js、ECharts）绘制
- 实时更新训练指标

**推荐方案**：方案1（更简单，功能完整）

### 3.2 Network GUI 实时可视化

#### 当前状态
- ✅ 3DGS训练脚本已集成network_gui
- ✅ 支持实时渲染预览
- ❌ 前端没有集成network_gui客户端

#### Network GUI 功能
- **实时渲染**：训练过程中实时显示当前Gaussians的渲染结果
- **交互控制**：可以调整视角、缩放等
- **训练控制**：可以暂停/继续训练

#### 技术细节
- **协议**：基于Socket的JSON通信
- **默认端口**：6009
- **数据流**：训练脚本 → network_gui服务器 → 客户端

#### 实现建议

**方案1：集成SIBR Viewers**
- 3DGS项目包含SIBR_viewers目录
- 可以编译为Web版本或使用原生客户端

**方案2：自定义Web客户端**
- 实现network_gui协议
- 使用WebGL/WebGPU渲染
- 需要实现Gaussian Splatting渲染器

**方案3：使用现有Web查看器**
- 使用Visionary或其他Web查看器
- 定期从训练输出目录读取最新PLY文件
- 实时更新预览

**推荐方案**：方案3（最简单，但延迟较高）或方案1（功能最完整）

---

## 四、实现建议

### 4.1 参数扩展实现

#### 前端扩展 (`GaussianSplattingPanel.vue`)

```typescript
// 扩展参数定义
const params = ref({
  // 基础参数（已有）
  iterations: 7000,
  resolution: 2,
  data_device: 'cpu' as 'cpu' | 'cuda',
  sh_degree: 3,
  
  // 新增高优先级参数
  test_iterations: [7000, 30000] as number[],
  save_iterations: [7000, 30000] as number[],
  white_background: false,
  quiet: false,
  disable_viewer: false,
  
  // 新增中优先级参数（可选，折叠显示）
  densify_from_iter: 500,
  densify_until_iter: 15000,
  densification_interval: 100,
  lambda_dssim: 0.2,
  opacity_reset_interval: 3000,
})
```

#### UI布局建议

```
┌─────────────────────────────────────┐
│ 基础参数（始终显示）                │
│ [iterations] [resolution] [device] │
│ [sh_degree]                        │
├─────────────────────────────────────┤
│ 评估参数（展开/收起）               │
│ [test_iterations] [save_iterations]│
│ [white_background] [quiet]          │
├─────────────────────────────────────┤
│ 高级参数（折叠，默认隐藏）          │
│ [densify_from_iter] ...             │
└─────────────────────────────────────┘
```

#### 后端扩展 (`gs_runner.py`)

```python
# 扩展参数传递
args = [
    GS_PYTHON,
    "train.py",
    "-s", dataset_dir,
    "-m", model_dir,
    "--iterations", str(int(train_params.get("iterations", 7000))),
    "--resolution", str(int(train_params.get("resolution", 2))),
    "--data_device", str(train_params.get("data_device", "cpu")),
    "--sh_degree", str(int(train_params.get("sh_degree", 3))),
]

# 新增参数
if "test_iterations" in train_params:
    test_iters = train_params["test_iterations"]
    if isinstance(test_iters, list):
        args.extend(["--test_iterations"] + [str(x) for x in test_iters])
    else:
        args.extend(["--test_iterations", str(test_iters)])

if "save_iterations" in train_params:
    save_iters = train_params["save_iterations"]
    if isinstance(save_iters, list):
        args.extend(["--save_iterations"] + [str(x) for x in save_iters])
    else:
        args.extend(["--save_iterations", str(save_iters)])

if train_params.get("white_background", False):
    args.append("--white_background")

if train_params.get("quiet", False):
    args.append("--quiet")

if train_params.get("disable_viewer", False):
    args.append("--disable_viewer")
```

### 4.2 TensorBoard集成实现

#### 后端实现

```python
# 在 gs_runner.py 中
import subprocess
import threading

def start_tensorboard(log_dir: str, port: int = 6006):
    """启动TensorBoard服务器"""
    cmd = ["tensorboard", "--logdir", log_dir, "--port", str(port)]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

# 在训练开始时
tb_process = start_tensorboard(model_dir, port=6006)
block.gs_statistics["tensorboard_port"] = 6006
block.gs_statistics["tensorboard_url"] = f"http://localhost:6006"
```

#### 前端实现

```vue
<!-- 在 GaussianSplattingPanel.vue 中添加 -->
<el-card v-if="block.gs_statistics?.tensorboard_url" class="tensorboard-card">
  <template #header>
    <span>训练指标 (TensorBoard)</span>
  </template>
  <iframe 
    :src="block.gs_statistics.tensorboard_url" 
    class="tensorboard-iframe"
    frameborder="0"
  />
</el-card>
```

### 4.3 Network GUI集成实现

#### 方案：定期更新PLY预览

```typescript
// 在训练过程中，定期检查最新的PLY文件
async function checkLatestPLY() {
  if (!isRunning.value) return
  
  try {
    const res = await gsApi.files(props.block.id)
    const plyFiles = res.data.files.filter(f => 
      f.type === 'gaussian' && f.name.includes('point_cloud.ply')
    )
    
    if (plyFiles.length > 0) {
      // 按迭代次数排序，获取最新的
      const latest = plyFiles.sort((a, b) => {
        const iterA = parseInt(a.name.match(/iteration_(\d+)/)?.[1] || '0')
        const iterB = parseInt(b.name.match(/iteration_(\d+)/)?.[1] || '0')
        return iterB - iterA
      })[0]
      
      // 更新预览
      if (latest.name !== currentPreviewFile.value) {
        currentPreviewFile.value = latest.name
        updatePreview(latest)
      }
    }
  } catch (e) {
    console.error('Failed to check latest PLY:', e)
  }
}

// 在训练运行时，每10秒检查一次
if (isRunning.value) {
  const plyCheckInterval = setInterval(checkLatestPLY, 10000)
}
```

---

## 五、优先级建议

### 第一阶段（立即实现）
1. ✅ **test_iterations** - 测试迭代点
2. ✅ **save_iterations** - 保存迭代点
3. ✅ **white_background** - 白色背景
4. ✅ **TensorBoard集成** - 训练指标可视化

### 第二阶段（短期实现）
5. **quiet** - 安静模式
6. **disable_viewer** - 禁用查看器
7. **densify_from_iter / densify_until_iter** - 密集化控制
8. **实时PLY预览更新** - 训练过程中预览

### 第三阶段（长期优化）
9. 其他高级参数（学习率、密集化参数等）
10. Network GUI完整集成
11. 参数预设（快速/标准/高质量）

---

## 六、总结

### 当前状态
- ✅ 基础参数已实现（4个）
- ❌ 缺少重要评估参数（test_iterations, save_iterations）
- ❌ 缺少训练可视化（TensorBoard, 实时预览）

### 建议
1. **优先扩展高优先级参数**（test_iterations, save_iterations, white_background）
2. **集成TensorBoard**（相对简单，功能强大）
3. **实现实时PLY预览**（训练过程中定期更新预览）

### 预期效果
- 用户可以更好地控制训练过程
- 可以实时监控训练指标
- 可以及时发现问题并调整参数

---

生成时间：2025-12-29
基于：3DGS train.py 和当前前端实现

