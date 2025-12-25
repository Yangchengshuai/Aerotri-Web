# InstantSfM 运行错误排查与分析

## 错误现象

在运行 InstantSfM 进行空三处理时，在 "Running global positioning" 阶段出现错误：

```
ValueError: bad marshal data (unknown type code)
```

## 错误堆栈

```
File "/root/miniconda3/envs/instantsfm/bin/ins-sfm", line 7, in <module>
sys.exit(entrypoint())
...
File "/root/miniconda3/envs/instantsfm/lib/python3.11/site-packages/sympy/polys/numberfields/__init__.py", line 27, in <module>
from .galoisgroups import galois_group
File "<frozen importlib._bootstrap_external>", line 729, in _compile_bytecode
ValueError: bad marshal data (unknown type code)
```

## 问题分析

### 1. 错误类型
`ValueError: bad marshal data (unknown type code)` 是 Python 字节码损坏或版本不匹配的典型错误。

### 2. 可能原因

1. **Python 字节码损坏**
   - `sympy` 包的 `.pyc` 文件损坏
   - 可能是由于不完整的安装或文件系统问题

2. **Python 版本不匹配**
   - 字节码是用不同版本的 Python 编译的
   - 当前环境是 Python 3.11，但某些包可能是用其他版本编译的

3. **环境污染**
   - conda 环境中的包版本冲突
   - 多个 Python 解释器混用

### 3. 影响范围
- 错误发生在 `sympy` 包的导入阶段
- 影响 InstantSfM 的全局定位（global positioning）阶段
- 导致整个空三流程失败

## 解决方案

### 方案 1：清理并重新安装 sympy（推荐）

```bash
conda activate instantsfm
pip uninstall sympy -y
pip install sympy --force-reinstall --no-cache-dir
```

### 方案 2：清理所有 Python 字节码缓存

```bash
conda activate instantsfm
find /root/miniconda3/envs/instantsfm/lib/python3.11/site-packages/sympy -name "*.pyc" -delete
find /root/miniconda3/envs/instantsfm/lib/python3.11/site-packages/sympy -name "__pycache__" -type d -exec rm -r {} +
python -c "import sympy; print('sympy OK')"
```

### 方案 3：重新创建 conda 环境（最彻底）

```bash
# 备份当前环境
conda env export -n instantsfm > instantsfm_backup.yml

# 删除并重建环境
conda deactivate
conda env remove -n instantsfm
conda create -n instantsfm python=3.11
conda activate instantsfm

# 重新安装依赖
cd /root/work/instantsfm
pip install -e .
pip install git+ssh://git@github.com/zitongzhan/bae.git
```

### 方案 4：使用 pip 重新安装所有依赖

```bash
conda activate instantsfm
pip install --force-reinstall --no-cache-dir sympy torch torchvision
```

## 验证步骤

1. **测试 sympy 导入**
   ```bash
   conda activate instantsfm
   python -c "import sympy; print('sympy version:', sympy.__version__)"
   ```

2. **测试 InstantSfM 导入**
   ```bash
   conda activate instantsfm
   python -c "import instantsfm; print('InstantSfM OK')"
   ```

3. **测试 ins-sfm 命令**
   ```bash
   conda activate instantsfm
   export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH
   ins-sfm --help
   ```

4. **使用小数据集测试**
   ```bash
   cd /root/work/instantsfm
   conda activate instantsfm
   export LD_LIBRARY_PATH=/root/opt/ceres-2.3-cuda/lib:$LD_LIBRARY_PATH
   ins-feat --data_path examples/kitchen
   ins-sfm --data_path examples/kitchen --manual_config_name colmap --export_txt
   ```

## 预防措施

1. **定期清理字节码缓存**
   ```bash
   find /root/miniconda3/envs/instantsfm -name "*.pyc" -delete
   find /root/miniconda3/envs/instantsfm -name "__pycache__" -type d -exec rm -r {} +
   ```

2. **使用环境锁定文件**
   - 保存 `requirements.txt` 或 `environment.yml`
   - 确保环境可重现

3. **避免混用包管理器**
   - 在 conda 环境中优先使用 conda 安装
   - 或统一使用 pip

## 临时解决方案

如果问题持续存在，可以考虑：

1. **跳过有问题的模块**（不推荐，可能影响功能）
2. **使用 Docker 容器**（隔离环境）
3. **降级 Python 版本**（如果兼容）

## 相关文件

- 错误日志：`/root/work/aerotri-web/data/outputs/ae8bdc79-df39-4bca-baad-63f74600b95d/run.log`
- InstantSfM 代码：`/root/work/instantsfm`
- 任务运行器：`/root/work/aerotri-web/backend/app/services/task_runner.py`

## 下一步

1. 执行方案 1（最快）
2. 如果失败，执行方案 2
3. 如果仍失败，考虑方案 3（重建环境）
4. 验证修复后，更新任务运行器以包含错误处理

