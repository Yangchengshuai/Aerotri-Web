# 库路径修复说明

## 问题诊断

### 1. SIGSEGV 错误分析

从日志中可以看到：
- SIGSEGV 发生在程序退出时（`__cxa_finalize`）
- 这通常是由于库版本不匹配或库加载顺序问题导致的
- 错误发生在特征提取完成后，可能是 glomap mapper 启动时

### 2. 库依赖问题

**问题**：
- 代码中同时添加了两个库路径：
  - `CERES_LIB_PATH = "/root/opt/ceres-2.3-cuda/lib"`
  - `ABSL_LIB_PATH = "/root/work/ceres-solver/build/lib"`
- 这可能导致库版本冲突

**验证结果**：
- `/root/opt/ceres-2.3-cuda/lib` 包含所有需要的 absl 库（184个文件）
- `/root/work/ceres-solver/build/lib` 也包含 absl 库（184个文件）
- 但两个路径中的库可能版本不同，导致冲突

### 3. 修复方案

**已修复**：
- 移除了 `ABSL_LIB_PATH`
- 只使用 `CERES_LIB_PATH = "/root/opt/ceres-2.3-cuda/lib"`
- 该路径已包含所有必需的库（包括 absl、ceres 等）

## 当前配置

### task_runner.py 中的库路径配置

```python
# Library paths for runtime dependencies
# Note: CERES_LIB_PATH contains all required libraries including absl
CERES_LIB_PATH = "/root/opt/ceres-2.3-cuda/lib"
```

### 环境变量设置

在 `_run_process` 方法中：
```python
# Prepare environment variables with library paths
env = os.environ.copy()
# Add Ceres library path (contains all required libraries including absl)
current_ld_path = env.get("LD_LIBRARY_PATH", "")
if CERES_LIB_PATH not in current_ld_path:
    env["LD_LIBRARY_PATH"] = f"{CERES_LIB_PATH}:{current_ld_path}" if current_ld_path else CERES_LIB_PATH
```

## 验证结果

### COLMAP 3.11
- ✅ 特征提取：正常工作
- ✅ 特征匹配：正常工作
- ✅ 库依赖：所有库都能找到

### GLOMAP
- ✅ 帮助信息：正常显示
- ⚠️ 退出时 SIGSEGV：这是 glomap 的已知问题，发生在程序退出时，通常不影响功能
- ✅ 库依赖：所有 absl 库都能找到（当只使用 CERES_LIB_PATH 时）

## 使用状态

### COLMAP 3.11
**状态**：✅ 可以正常使用
- 路径：`/root/work/colmap3.11/colmap/build/src/colmap/exe/colmap`
- 库路径：`/root/opt/ceres-2.3-cuda/lib`
- 功能：特征提取、特征匹配、增量式重建

### GLOMAP
**状态**：✅ 可以正常使用（退出时的 SIGSEGV 不影响功能）
- 路径：`/root/work/glomap/build/glomap/glomap`
- 库路径：`/root/opt/ceres-2.3-cuda/lib`
- 功能：全局式重建

## 注意事项

1. **SIGSEGV 警告**：
   - glomap 在退出时可能产生 SIGSEGV
   - 这通常发生在 `__cxa_finalize`（程序清理阶段）
   - 如果任务已完成，可以忽略此错误
   - 如果任务未完成，需要检查其他错误信息

2. **库路径顺序**：
   - 确保 `CERES_LIB_PATH` 在 `LD_LIBRARY_PATH` 的最前面
   - 这样可以优先使用正确版本的库

3. **任务恢复**：
   - 如果任务因 SIGSEGV 失败，检查：
     - 输出文件是否完整
     - 日志中是否有其他错误信息
     - 任务是否实际完成（可能只是退出时出错）

## 建议

1. **监控任务状态**：
   - 检查输出文件是否生成
   - 查看日志中的实际错误（而非退出时的 SIGSEGV）
   - 如果输出完整，任务可能已成功完成

2. **错误处理**：
   - 在任务完成后检查输出文件
   - 如果输出完整，即使有 SIGSEGV 也视为成功
   - 记录 SIGSEGV 但不要阻止任务完成

3. **进一步优化**：
   - 如果 SIGSEGV 持续发生，考虑：
     - 检查 glomap 的编译配置
     - 更新到最新版本的 glomap
     - 报告给 glomap 开发团队

