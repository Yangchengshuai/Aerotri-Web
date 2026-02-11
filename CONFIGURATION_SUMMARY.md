# 诊断Agent配置系统实现总结

## 实现内容

本次更新实现了完整的诊断 Agent 配置系统和上下文持久化功能，为项目开源做好准备。

---

## ✅ 完成的功能

### 1. 配置系统增强

#### 新增配置项 (`config/defaults.yaml`)

| 配置项 | 类型 | 默认值 | 说明 |
|---------|------|---------|------|
| `diagnostic.enabled` | boolean | `false` | 全局开关，默认关闭 |
| `diagnostic.openclaw_cmd` | string | `"openclaw"` | OpenClaw CLI 路径 |
| `diagnostic.agent_id` | string | `"main"` | Agent ID |
| `diagnostic.agent_memory_path` | Path | - | Agent 知识库路径 |
| `diagnostic.history_log_path` | Path | - | 诊断历史路径 |
| `diagnostic.claude_md_path` | Path | - | 项目文档路径 |
| `diagnostic.context_output_dir` | Path | - | 调试上下文输出目录 |
| `diagnostic.timeout_seconds` | integer | `180` | 调用超时 |
| `diagnostic.auto_fix` | boolean | `false` | 自动修复开关 |

#### 路径配置特性

- ✅ 支持绝对路径和相对路径
- ✅ 绝对路径直接使用，不修改
- ✅ 相对路径相对于 `backend/config/` 解析
- ✅ 环境变量覆盖支持

#### 环境变量

```bash
export AEROTRI_DIAGNOSTIC_AGENT_MEMORY="/path/to/AerotriWeb_AGENT.md"
export AEROTRI_DIAGNOSTIC_HISTORY_LOG="/path/to/diagnosis_history.log"
export AEROTRI_DIAGNOSTIC_CLAUDE_MD="/path/to/CLAUDE.md"
export AEROTRI_DIAGNOSTIC_CONTEXT_DIR="/path/to/contexts"
```

### 2. 代码实现

#### 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `app/conf/settings.py` | 添加 `DiagnosticConfig` 类，支持路径解析 |
| `app/services/openclaw_diagnostic_agent.py` | 修复参数兼容性，添加上下文持久化 |
| `app/services/task_runner_integration.py` | 参数别名支持 (`auto_fix` → `auto_diagnose`) |
| `app/services/notification/templates.py` | 添加 `diagnosis_completed` 模板 |
| `app/services/notification/manager.py` | 添加 `notify_diagnosis_completed()` 方法 |

#### 参数兼容性修复

**问题**: `gs_runner.py` 传递 `auto_fix=True`，但 `task_runner_integration.py` 期望 `auto_diagnose`

**解决方案**:
1. 修复 `gs_runner.py`: 改为 `auto_diagnose=True`
2. 增强 `task_runner_integration.py`: 接受 `auto_fix` 作为别名

### 3. 上下文持久化

#### 输出目录

```bash
/root/work/aerotri-web/data/diagnostics/contexts/
```

#### 文件格式

**命名**: `YYYYMMDD_HHMMSS_{block_id}_{task_type}_context.md`

**内容结构**:
```markdown
# 诊断上下文 - 20260211_183022

**Block ID**: c728ccfa-f967-4fb4-8480-33b92633ea2f
**Task Type**: gs
**Stage**: training
**Timestamp**: 2026-02-11T18:30:22.123456

---

## 原始上下文
```json
{
  "block_info": {...},
  "task_info": {...},
  "system_status": {...},
  "error_info": {...}
}
```

---

## 发送给OpenClaw的Prompt
```
（完整的诊断请求内容）
```
```

#### 用途

1. **调试**: 验证发送给 OpenClaw 的上下文准确且无冗余
2. **优化**: 根据实际内容调整 Prompt 模板
3. **验证**: 确认包含所有必要信息

### 4. 通知功能完善

#### 双通知机制

```
任务失败
  ↓
立即发送 "task_failed" 通知（钉钉）
  ↓
后台执行 AI 诊断（不阻塞主流程）
  ↓
诊断完成 → 发送 "diagnosis_completed" 通知（钉钉）
```

#### 诊断完成通知模板

```markdown
### AI 诊断分析

**Block**: test_block
**任务类型**: 3DGS 训练

---

### 🤖 AI 诊断结果

**错误类型**: CUDA OOM

**根本原因**: GPU 显存不足，数据集过大

**修复建议**:
1. 降低训练参数 `--images`
2. 减少 `--densify_until_iter` 迭代次数
3. 使用更大显存的 GPU (RTX 5090 32GB)
```

### 5. 配置文件

#### 新增文件

1. **`config/CONFIGURATION_GUIDE.md`** - 完整配置指南
   - 10 大部分配置说明
   - 表格化参数说明
   - 配置场景示例
   - 常见问题解答

2. **`config/diagnostic.yaml.example`** - 诊断配置示例

3. **`verify_diagnostic_config_and_context.py`** - 配置验证脚本

4. **`DIAGNOSTIC_CONFIG_GUIDE.md`** - 诊断功能专门说明

#### 已更新文件

```
aerotri-web/backend/config/
├── defaults.yaml           # ✅ 添加诊断配置
├── settings.yaml.example   # ✅ 更新配置示例
├── diagnostic.yaml.example # ✅ 新增诊断配置示例
├── CONFIGURATION_GUIDE.md  # ✅ 新增完整配置指南
└── DIAGNOSTIC_CONFIG_GUIDE.md # ✅ 新增诊断功能说明

aerotri-web/backend/
├── app/conf/settings.py      # ✅ 添加 DiagnosticConfig
├── app/services/
│   ├── openclaw_diagnostic_agent.py       # ✅ 上下文持久化
│   ├── task_runner_integration.py        # ✅ 参数兼容性
│   └── notification/
│       ├── manager.py                 # ✅ 诊断完成通知
│       └── templates.py              # ✅ 通知模板
└── verify_diagnostic_config_and_context.py # ✅ 新增验证脚本
```

### 6. 测试验证

#### 配置生效性验证

```bash
$ python3 -c "from app.conf.settings import get_settings; print(get_settings().diagnostic.enabled)"
True  # ✅ 配置正确加载
```

#### 路径配置验证

| 路径 | 状态 |
|------|------|
| `agent_memory_path` | ✅ 已创建初始模板 |
| `history_log_path` | ✅ 存在（代码自动创建） |
| `claude_md_path` | ✅ 存在 |
| `context_output_dir` | ✅ 已创建目录 |

#### 上下文持久化测试

```bash
$ python3 verify_diagnostic_config_and_context.py

=== 诊断Agent配置完整验证 ===
======================================================================

路径配置验证
======================================================================

配置的路径:
  agent_memory_path: /root/work/aerotri-web/data/diagnostics/AerotriWeb_AGENT.md
  ...

路径类型检查:
  agent_memory_path: ✅ 绝对
  history_log_path: ✅ 绝对
  claude_md_path: ✅ 绝对
  context_output_dir: ✅ 绝对

上下文持久化功能验证
======================================================================

✅ 成功创建测试上下文文件:
   /root/work/aerotri-web/data/diagnostics/contexts/20260211_185819_123_gs_context.md

文件内容预览:
----------------------------------------------------------------------
# 诊断上下文 - 20260211_185819

**Block ID**: 123
...
```

### 7. Agent 知识库

#### 创建的初始模板

**文件**: `/root/work/aerotri-web/data/diagnostics/AerotriWeb_AGENT.md`

**内容结构**:
1. **常见错误类型**:
   - CUDA OOM (显存不足)
   - Bundle Adjustment 失败
   - OpenMVS 密集化失败

2. **已解决案例**:
   - 案例 #1: Block c728ccfa CUDA OOM
   - 时间、问题、根因、解决方案

3. **更新日志**: 记录知识库变更历史

---

## 🎯 配置优先级

```
环境变量 (最高)
    ↓
config/settings.yaml (用户自定义）
    ↓
config/defaults.yaml (默认值）
```

---

## 📋 使用说明

### 开发环境

```yaml
# config/settings.yaml
debug: true
log_level: "DEBUG"
diagnostic:
  enabled: false  # 开发时关闭，避免频繁调用
```

### 生产环境（启用诊断）

```yaml
# config/settings.yaml
diagnostic:
  enabled: true
  timeout_seconds: 180
  agent_memory_path: "/root/work/aerotri-web/data/diagnostics/AerotriWeb_AGENT.md"
```

### 环境变量覆盖（特殊情况）

```bash
# 临时使用不同的 OpenClaw Agent
export AEROTRI_DIAGNOSTIC_AGENT_MEMORY="/custom/path/agent.md"
export AEROTRI_DIAGNOSTIC_CONTEXT_DIR="/tmp/contexts"
```

---

## ✅ 验收检查清单

- [x] 配置系统支持绝对路径和相对路径
- [x] 配置系统支持环境变量覆盖
- [x] 诊断功能可通过配置文件启用/禁用
- [x] 诊断上下文自动持久化到文件
- [x] 参数兼容性问题已修复 (auto_fix → auto_diagnose)
- [x] 双通知机制工作正常（立即失败 + 延迟诊断）
- [x] 创建完整的配置文档和指南
- [x] 添加配置验证脚本

---

## 📊 文件统计

**提交**: `828afca`

**文件变更**: 27 个文件，2584 行添加，122 行删除

**新增文件**:
- `config/CONFIGURATION_GUIDE.md` - 配置指南
- `config/diagnostic.yaml.example` - 诊断配置示例
- `DIAGNOSTIC_CONFIG_GUIDE.md` - 诊断功能说明
- `verify_diagnostic_config_and_context.py` - 验证脚本
- `data/diagnostics/AerotriWeb_AGENT.md` - Agent 知识库初始模板

**修改文件**:
- `app/conf/settings.py` - 配置类增强
- `app/services/openclaw_diagnostic_agent.py` - 上下文持久化
- `app/services/task_runner_integration.py` - 参数兼容性
- `app/services/notification/manager.py` - 诊断完成通知
- `app/services/notification/templates.py` - 通知模板
- `config/defaults.yaml` - 默认配置

---

**最后更新**: 2026-02-11
**Git 提交**: `828afca`
