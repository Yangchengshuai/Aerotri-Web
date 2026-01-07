# SPZ numpy 版本兼容性问题修复报告

## 一、问题描述

在使用 SPZ Python bindings 加载 SPZ 文件时，出现错误：

```
No module named 'numpy._core'
```

错误发生在 subprocess 调用 conda 环境的 Python 加载 SPZ 文件后，尝试反序列化数据时。

## 二、问题分析

### 2.1 错误信息

从日志文件可以看到：
- SPZ 文件成功生成
- 使用 SPZ Python bindings 加载时失败
- 错误：`No module named 'numpy._core'`

### 2.2 根本原因

**numpy 版本不匹配导致 pickle 序列化/反序列化失败**：

1. **环境版本差异**：
   - 系统 Python: numpy 1.24.4
   - Conda 环境 (spz-env): numpy 2.2.6

2. **numpy 2.x 的变化**：
   - numpy 2.x 引入了 `numpy._core` 模块
   - numpy 1.x 没有此模块
   - pickle 序列化的对象包含 numpy 数组时，会记录 numpy 的内部结构

3. **问题流程**：
   ```
   Conda Python (numpy 2.2.6)
     ↓
   加载 SPZ 文件，生成 numpy arrays
     ↓
   pickle.dump() 序列化（使用 numpy 2.x 格式）
     ↓
   系统 Python (numpy 1.24.4)
     ↓
   pickle.load() 反序列化
     ↓
   ❌ 失败：找不到 numpy._core 模块
   ```

### 2.3 数据验证

```bash
System numpy version: 1.24.4
Conda numpy version: 2.2.6
```

版本差异导致 pickle 不兼容。

## 三、解决方案

### 3.1 修复策略

**使用 numpy.savez 替代 pickle**：
- `numpy.savez` 是版本无关的二进制格式
- numpy 1.x 和 2.x 都可以读取
- 避免了 pickle 的版本依赖问题

### 3.2 修复实现

**文件**: 
- `backend/app/services/spz_loader_helper.py`
- `backend/app/services/spz_loader.py`

**关键修改**：

1. **Helper 脚本**（spz_loader_helper.py）：
   ```python
   # 修复前：使用 pickle
   pickle.dump(data, sys.stdout.buffer)
   
   # 修复后：使用 numpy.savez
   np.savez_compressed(output_file, **save_dict)
   print(output_file, file=sys.stdout)  # 输出文件路径
   ```

2. **主加载函数**（spz_loader.py）：
   ```python
   # 修复前：使用 pickle
   data = pickle.loads(result.stdout)
   
   # 修复后：使用 numpy.load
   output_file = result.stdout.strip()  # 获取文件路径
   npz_data = np.load(output_file, allow_pickle=False)
   data = extract_from_npz(npz_data)
   Path(output_file).unlink()  # 清理临时文件
   ```

### 3.3 数据传递流程

修复后的流程：
```
Conda Python (numpy 2.2.6)
  ↓
加载 SPZ 文件
  ↓
numpy.savez_compressed() 保存到临时文件
  ↓
输出文件路径到 stdout
  ↓
系统 Python (numpy 1.24.4)
  ↓
读取文件路径
  ↓
numpy.load() 加载（版本兼容）
  ↓
提取数据
  ↓
删除临时文件
```

## 四、技术细节

### 4.1 numpy.savez 的优势

1. **版本兼容性**：
   - numpy.savez 格式在 numpy 1.x 和 2.x 之间兼容
   - 不依赖 Python pickle 协议

2. **性能**：
   - 支持压缩：`np.savez_compressed()`
   - 二进制格式，效率高

3. **类型安全**：
   - 保留 numpy 数组的 dtype
   - 不需要额外的类型转换

### 4.2 临时文件管理

- 使用 `tempfile.NamedTemporaryFile(delete=False)` 创建临时文件
- Helper 脚本输出文件路径到 stdout
- 主进程加载后立即删除临时文件
- 异常情况下也会尝试清理

### 4.3 错误处理

- 文件路径验证
- 加载失败时的清理
- 清晰的错误信息

## 五、修复验证

### 5.1 跨版本测试

测试结果：
```
✓ 使用 conda Python (numpy 2.2.6) 创建 npz 文件
✓ 使用系统 Python (numpy 1.24.4) 加载 npz 文件
✓ 数据完整性验证通过
✓ 跨版本兼容性确认
```

### 5.2 实际数据测试

使用实际 SPZ 文件测试：
- 文件大小：191.64 MB
- 点数：7,934,875
- SH degree：3
- 所有数据正确加载

## 六、修复文件清单

1. **backend/app/services/spz_loader_helper.py**
   - 移除 pickle 依赖
   - 使用 numpy.savez_compressed 保存数据
   - 输出临时文件路径到 stdout

2. **backend/app/services/spz_loader.py**
   - 移除 pickle 依赖
   - 使用 numpy.load 加载数据
   - 添加临时文件清理逻辑

## 七、代码优化

### 7.1 边界情况处理

- ✅ 处理 SH 系数为 None 的情况
- ✅ 处理空数组的情况
- ✅ 验证文件路径有效性
- ✅ 确保临时文件清理

### 7.2 性能优化

- 使用 `np.savez_compressed()` 减少文件大小
- 及时清理临时文件
- 避免内存泄漏

## 八、总结

**问题根源**：numpy 版本不匹配（1.24.4 vs 2.2.6）导致 pickle 序列化/反序列化失败。

**解决方案**：使用 numpy.savez 替代 pickle，实现版本无关的数据传递。

**修复状态**：✅ 已修复并验证通过

**优势**：
- ✅ 版本兼容性好
- ✅ 性能优秀（支持压缩）
- ✅ 类型安全
- ✅ 代码简洁

---

**修复时间**: 2026-01-07
**影响范围**: SPZ 文件加载功能（subprocess 模式）
**向后兼容**: ✅ 是（不影响直接导入模式）
