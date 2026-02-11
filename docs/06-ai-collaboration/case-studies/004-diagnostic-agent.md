# Case Study #004: 诊断 Agent 系统

> **问题**: 任务失败后需要人工诊断，耗时且容易遗漏
> **解决方案**: AI 驱动的智能诊断 Agent
> **关键决策**: OpenClaw CLI 集成
> **技术亮点**: 复利工程效应实践

---

## 背景

### 问题

1. 任务失败后需要手动分析日志
2. 相似问题反复出现，没有知识积累
3. 新人难以快速定位问题

---

## 技术方案

### 系统架构

```
任务失败 → 收集上下文 → 组装 Prompt → OpenClaw 分析 → 更新知识库
```

### 代码实现

**文件**: `aerotri-web/backend/app/services/openclaw_diagnostic_agent.py`

```python
class AerotriWebDiagnosticAgent:
    """诊断 Agent."""

    async def diagnose_failure(
        self,
        block_id: int,
        task_type: str,
        error_message: str,
        stage: Optional[str] = None,
    ):
        """诊断任务失败."""

        # 1. 收集上下文
        context = await diagnostic_collector.collect_failure_context(
            block_id, task_type, error_message, stage
        )

        # 2. 组装 Prompt
        prompt = await self._build_diagnosis_prompt(context)

        # 3. 发送给 OpenClaw
        response = await self._send_to_openclaw(prompt)

        # 4. 解析响应
        diagnosis = self._parse_openclaw_response(response)

        # 5. 更新知识库
        await self._update_knowledge_base(context, diagnosis)

        return diagnosis
```

---

## 经验总结

### 1. 精准上下文

```python
# 只提供相关信息
MAX_LOG_LINES = 500  # 最多 500 行日志
MAX_FILE_SIZE = 5 * 1024 * 1024  # 最多 5MB
```

### 2. 复利工程效应

每次诊断后更新知识库：
- 新模式 → `AerotriWeb_AGENT.md`
- 历史记录 → `diagnosis_history.log`

### 3. 可追溯性

```python
{
    "error_type": "CUDA OOM",
    "code_location": "task_runner.py:123",
    "fix_suggestion": "降低 batch_size"
}
```

---

**相关文件**:
- `openclaw_diagnostic_agent.py` - Agent 核心逻辑
- `diagnostic_context_collector.py` - 上下文收集器
- `task_runner_integration.py` - 任务集成钩子

