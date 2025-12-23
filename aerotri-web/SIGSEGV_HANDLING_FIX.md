# SIGSEGV 退出错误处理修复

## 问题描述

COLMAP/GLOMAP 在完成工作后退出时经常发生 SIGSEGV（段错误），这导致：
- 任务被标记为失败
- 无法继续到下一阶段（如特征匹配、mapper）
- 尽管实际工作已完成，输出有效

## 问题分析

### 错误模式
```
*** SIGSEGV (@0x1) received by PID XXX from PID 1; stack trace: ***
@ ... __cxa_finalize
@ ... exit
@ ... __libc_start_main
```

这表明错误发生在程序退出时的清理阶段（`__cxa_finalize`），而不是实际工作阶段。

### 验证结果
- 特征提取完成后，数据库包含 435 张图像和 435 条关键点记录
- 说明特征提取实际已完成，只是在退出时崩溃

## 修复方案

### 1. 特征提取错误处理

在 `_run_feature_extraction` 方法中添加输出验证：

```python
try:
    await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
except RuntimeError as e:
    # Check if feature extraction actually completed despite SIGSEGV on exit
    if "exited with code" in str(e) and os.path.exists(database_path):
        import sqlite3
        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.execute("SELECT COUNT(*) FROM images")
            image_count = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM keypoints")
            keypoint_count = cursor.fetchone()[0]
            conn.close()
            
            if image_count > 0 and keypoint_count > 0:
                ctx.write_log_line(f"Feature extraction completed despite exit error. Found {image_count} images, {keypoint_count} keypoints.")
                # Continue execution - output is valid
                return
        except Exception:
            pass
    # Re-raise if output validation failed
    raise
```

### 2. 特征匹配错误处理

在 `_run_matching` 方法中添加输出验证：

```python
try:
    await self._run_process(cmd, ctx, db, block_id, coarse_stage=coarse_stage)
except RuntimeError as e:
    # Check if matching actually completed despite SIGSEGV on exit
    if "exited with code" in str(e) and os.path.exists(database_path):
        import sqlite3
        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.execute("SELECT COUNT(*) FROM matches")
            match_count = cursor.fetchone()[0]
            conn.close()
            
            if match_count > 0:
                ctx.write_log_line(f"Matching completed despite exit error. Found {match_count} matches.")
                # Continue execution - output is valid
                return
        except Exception:
            pass
    # Re-raise if output validation failed
    raise
```

## 验证逻辑

### 特征提取验证
- 检查数据库是否存在
- 检查 `images` 表是否有记录
- 检查 `keypoints` 表是否有记录
- 如果都有，则认为特征提取成功

### 特征匹配验证
- 检查数据库是否存在
- 检查 `matches` 表是否有记录
- 如果有，则认为特征匹配成功

## 效果

1. **任务连续性**：
   - 即使特征提取退出时 SIGSEGV，如果输出有效，任务会继续到特征匹配阶段
   - 即使特征匹配退出时 SIGSEGV，如果输出有效，任务会继续到 mapper 阶段

2. **错误处理**：
   - 如果输出无效，仍然会抛出错误
   - 如果输出有效，记录警告但继续执行

3. **日志记录**：
   - 记录验证结果和找到的数据量
   - 便于调试和问题追踪

## 使用建议

1. **监控日志**：
   - 查看是否有 "completed despite exit error" 的日志
   - 确认输出验证结果

2. **任务状态**：
   - 如果任务继续执行，说明输出验证通过
   - 如果任务失败，检查日志中的具体错误

3. **数据完整性**：
   - 定期检查数据库中的数据量
   - 确保每个阶段都有预期的输出

## 注意事项

1. **SIGSEGV 的根本原因**：
   - 这可能是 COLMAP/GLOMAP 的已知问题
   - 与库版本或编译配置有关
   - 当前修复是工作区解决方案

2. **输出验证的局限性**：
   - 只检查数据是否存在，不检查数据完整性
   - 如果数据部分损坏，可能无法检测

3. **性能影响**：
   - 每次错误时都会查询数据库
   - 影响很小，但需要注意

## 后续改进

1. **更完善的验证**：
   - 检查数据完整性（如关键点数量是否合理）
   - 检查数据一致性

2. **预防措施**：
   - 调查 SIGSEGV 的根本原因
   - 考虑更新 COLMAP/GLOMAP 版本
   - 检查编译配置

3. **错误报告**：
   - 收集 SIGSEGV 的详细信息
   - 报告给 COLMAP/GLOMAP 开发团队

