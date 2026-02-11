# 诊断Agent配置指南

## 路径配置

### 支持的路径类型

诊断Agent配置中的路径参数支持**绝对路径**和**相对路径**：

| 参数 | 说明 | 绝对路径示例 | 相对路径示例 |
|------|------|-------------|-------------|
| `agent_memory_path` | Agent知识库 | `/root/work/.../AerotriWeb_AGENT.md` | `./data/diagnostics/AerotriWeb_AGENT.md` |
| `history_log_path` | 诊断历史日志 | `/root/work/.../diagnosis_history.log` | `./data/diagnostics/diagnosis_history.log` |
| `claude_md_path` | 项目文档 | `/root/work/.../CLAUDE.md` | `./../../CLAUDE.md` |
| `context_output_dir` | 上下文输出目录 | `/root/work/.../contexts` | `./data/diagnostics/contexts` |

### 路径解析规则

1. **绝对路径**：直接使用，不修改
   ```yaml
   agent_memory_path: "/root/work/aerotri-web/data/diagnostics/AerotriWeb_AGENT.md"
   ```

2. **相对路径**：相对于 `backend/config/` 目录解析
   ```yaml
   # 从 backend/config/ 解析
   agent_memory_path: "../data/diagnostics/AerotriWeb_AGENT.md"
   # 解析为: /root/work/aerotri-web/backend/data/diagnostics/...
   ```

3. **推荐配置**：使用绝对路径，避免混淆
   ```yaml
   agent_memory_path: "/root/work/aerotri-web/data/diagnostics/AerotriWeb_AGENT.md"
   history_log_path: "/root/work/aerotri-web/data/diagnostics/diagnosis_history.log"
   claude_md_path: "/root/work/aerotri-web/CLAUDE.md"
   context_output_dir: "/root/work/aerotri-web/data/diagnostics/contexts"
   ```

---

## 环境变量配置

支持通过环境变量覆盖所有路径配置：

```bash
# 导出环境变量（可选，优先级高于配置文件）
export AEROTRI_DIAGNOSTIC_AGENT_MEMORY="/custom/path/to/AerotriWeb_AGENT.md"
export AEROTRI_DIAGNOSTIC_HISTORY_LOG="/custom/path/to/diagnosis_history.log"
export AEROTRI_DIAGNOSTIC_CLAUDE_MD="/custom/path/to/CLAUDE.md"
export AEROTRI_DIAGNOSTIC_CONTEXT_DIR="/custom/path/to/contexts"
```

---

## 配置优先级

1. **环境变量**（最高优先级）
2. `config/settings.yaml` - 用户自定义配置
3. `config/defaults.yaml` - 默认配置

---

## 上下文持久化功能

### 功能说明

启用诊断后，系统会自动将发送给OpenClaw的上下文信息保存到文件，用于：
1. **调试**：查看传递给OpenClaw的完整上下文
2. **验证**：确认上下文信息准确且无冗余
3. **优化**：根据实际上下文优化Prompt模板

### 输出目录

```
/root/work/aerotri-web/data/diagnostics/contexts/
├── 20260211_183022_c728ccfa_gs_context.md
├── 20260211_184555_7a7a2dbe_gs_context.md
└── ...
```

### 文件格式

```markdown
# 诊断上下文 - 20260211_183022

**Block ID**: c728ccfa-f967-4fb4-8480-33b92633ea2f
**Task Type**: gs
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
# 诊断请求
...
（完整的Prompt内容）
```
```

---

## 使用示例

### 查看上下文文件

```bash
# 列出最近的上下文文件
ls -lt /root/work/aerotri-web/data/diagnostics/contexts/ | head -10

# 查看最新的上下文
cat /root/work/aerotri-web/data/diagnostics/contexts/$(ls -t /root/work/aerotri-web/data/diagnostics/contexts/ | head -1 | awk '{print $NF}')

# 检查上下文内容
head -100 /root/work/aerotri-web/data/diagnostics/contexts/20260211_183022_c728ccfa_gs_context.md
```

### 验证上下文质量

1. **完整性检查**：确认包含所有必要信息
   - Block信息
   - 任务类型和阶段
   - 错误信息
   - 系统状态
   - GPU状态

2. **冗余检查**：确认无重复信息
   - 系统状态不应重复
   - 日志不应包含大量重复内容

3. **准确性检查**：确认信息正确
   - 错误消息完整
   - Block ID正确
   - 时间戳准确

---

## 故障排查

### 问题1: 文件未创建

**检查**:
```bash
# 检查目录是否存在
ls -ld /root/work/aerotri-web/data/diagnostics/contexts

# 检查配置
python3 -c "
from app.conf.settings import get_settings
settings = get_settings()
print('context_output_dir:', settings.diagnostic.context_output_dir)
print('exists:', settings.diagnostic.context_output_dir.exists())
"
```

### 问题2: 路径解析错误

**症状**: 日志显示路径不存在

**解决**:
1. 使用绝对路径配置
2. 确保路径以 `/` 开头
3. 确保目录存在（系统会自动创建）

### 问题3: 上下文信息不完整

**检查**: 查看上下文文件，确认包含所有必要部分

---

## 最佳实践

1. **使用绝对路径**：避免相对路径解析错误
2. **定期清理**：删除旧的上下文文件，避免占用过多磁盘空间
3. **查看上下文**：在开发阶段定期查看，确保上下文质量
4. **优化Prompt**：根据实际上下文内容调整Prompt模板

---

**配置文件位置**: `/root/work/Aerotri-Web/aerotri-web/backend/config/defaults.yaml`
**环境变量前缀**: `AEROTRI_DIAGNOSTIC_`
