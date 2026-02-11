# Aerotri-Web AI 诊断 Agent 系统 - 设计文档

> 🎯 **目标**: 构建一个有长期记忆、可追溯、经验积累的诊断 Agent 系统

---

## 📋 设计原则

基于你的 **Vibe Coding 最佳实践**，本系统遵循以下原则：

1. **复利工程效应** (#23): 每次诊断经验沉淀到知识库，形成知识复利
2. **精准上下文** (#31): 只提供相关的日志和代码，避免信息过载
3. **分析对应代码** (#32): 诊断结果明确关联到具体代码位置
4. **增加 log 输出** (#21): 每个关键阶段都有日志，便于 AI 定位问题
5. **AI 团队管理者** (#33): 开发者作为 AI 团队的管理者，而非执行者

---

## 🏗️ 系统架构

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                       应用层                                 │
│  task_runner.py, openmvs_runner.py, gs_runner.py, etc.     │
│  捕获异常 → on_task_failure()                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      服务层                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  DiagnosticContextCollector                           │  │
│  │  - 收集上下文（Block、Logs、系统状态）                 │  │
│  │  - 格式化为 AI 可读的 Prompt                           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  AerotriWebDiagnosticAgent                            │  │
│  │  - 组装完整 Prompt（含历史和经验）                     │  │
│  │  - 调用 OpenClaw 进行分析                             │  │
│  │  - 解析响应并执行自动修复                              │  │
│  │  - 更新知识库和历史记录                                │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                  │
│  ┌───────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │ AerotriWeb_AGENT. │  │ diagnosis_history│  │ CLAUDE.md │ │
│  │       md          │  │      .log        │  │           │ │
│  │ (问题模式库)       │  │  (历史任务记录)   │  │ (系统经验) │ │
│  └───────────────────┘  └──────────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 知识库设计

### 1. AerotriWeb_AGENT.md（问题模式库）

**结构**:
```markdown
# Aerotri-Web 诊断 Agent 知识库

## [错误类型]

**错误特征**:
```
[示例日志]
```

**常见场景**:
- 场景 1
- 场景 2

**根因分析**:
[分析]

**修复建议**:
1. 建议 1
2. 建议 2

**预防措施**:
- 预防 1

**历史案例**:
- Block #XXX (YYYY-MM-DD): [简述]

**相关资源**:
- [链接]
```

**维护规则**:
- 每个新问题模式添加一个章节
- 历史案例按时间倒序排列
- 使用标签分类（如 `colmap`, `cuda`, `oom`）

### 2. diagnosis_history.log（历史任务记录）

**结构**:
```markdown
## 条目 #N - YYYY-MM-DD HH:MM:SS UTC

### 任务信息
- **Block ID**: 123
- **任务类型**: sfm
- **失败阶段**: bundle_adjustment

### 错误信息
```
[错误日志]
```

### 诊断结果
- **错误类型**: XXX
- **根本原因**: YYY

### 修复建议
1. 建议 1
2. 建议 2

### 执行结果
- **是否已修复**: 是/否

### 经验更新
- ✅ 新问题模式 / 已有模式

### OpenClaw 分析
- **置信度**: 0.95

### 标签
`tag1`, `tag2`

---
```

**维护规则**:
- 每次诊断后追加（不修改历史）
- 条目编号递增
- 定期统计（按月/按年）

### 3. CLAUDE.md（系统经验）

**作用**: 提供项目级上下文，帮助 Agent 理解系统架构

**关键内容**:
- 项目概述
- 架构设计
- API 端点
- 环境变量
- 常见问题
- 相关代码位置

---

## 🔄 工作流程

### 自动诊断流程（主要流程）

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 任务失败                                                  │
│    task_runner.py 捕获异常                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 触发诊断钩子                                              │
│    await on_task_failure(                                   │
│      block_id, task_type, error_message, stage              │
│    )                                                         │
│    → 异步执行（不阻塞主流程）                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 收集上下文                                                │
│    DiagnosticContextCollector.collect_failure_context()      │
│    → Block 信息                                              │
│    → Log 文件（最近 N 行）                                    │
│    → 系统状态（GPU、内存、磁盘）                              │
│    → 目录结构                                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 组装 Prompt                                               │
│    AerotriWebDiagnosticAgent._build_diagnosis_prompt()       │
│    → 基础上下文（失败摘要、Block 信息、系统状态、日志）         │
│    → Agent 经验（AerotriWeb_AGENT.md）                       │
│    → 历史案例（diagnosis_history.log，最近相似案例）          │
│    → CLAUDE.md（系统经验，可选）                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 发送给 OpenClaw                                           │
│    _send_to_openclaw(prompt)                                 │
│    → 通过钉钉 Webhook 发送                                   │
│    → 等待 AI 分析（超时 60 秒）                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 解析诊断结果                                              │
│    _parse_openclaw_response(raw_response)                    │
│    → 提取 JSON                                               │
│    → 获取：错误类型、根本原因、置信度、修复建议                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. 尝试自动修复                                              │
│    _attempt_auto_fix(block_id, diagnosis)                    │
│    → 如果可以自动修复（如相机模型、权限等）                    │
│    → 执行修复操作                                            │
│    → 返回修复结果                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. 更新知识库                                                │
│    _update_knowledge_base(context, diagnosis, auto_fixed)    │
│    → 如果是新问题模式：添加到 AerotriWeb_AGENT.md            │
│    → 更新历史案例统计                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. 记录历史                                                  │
│    _append_to_history(context, diagnosis, auto_fixed)        │
│    → 追加到 diagnosis_history.log                            │
│    → 生成条目编号                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. 返回诊断结果                                             │
│     → success: bool                                          │
│     → diagnosis: dict                                        │
│     → auto_fixed: bool                                       │
└─────────────────────────────────────────────────────────────┘
```

### 主动对话流程（开发任务）

```
开发者 → 钉钉 → OpenClaw → AerotriWebDiagnosticAgent.chat_with_agent()
                              ↓
                         组装 Prompt
                              ↓
                         OpenClaw 分析
                              ↓
                         返回响应
                              ↓
                         钉钉 → 开发者
```

---

## 🎯 上下文设计

### 核心思想：精准上下文（#31）

**❌ 避免**:
- 提供整个 CLAUDE.md（16KB+）
- 提供整个日志文件（可能数 MB）
- 提供无关的代码文件

**✅ 推荐**:
- 只提供相关的章节（如 "Partition SfM"）
- 只提供最近的 N 行日志（如 500 行）
- 只提供相关的代码文件（如 task_runner.py）

### Prompt 组装策略

```
1. 基础上下文（必须）
   - 失败摘要
   - Block 信息
   - 系统状态
   - 日志内容（最近 500 行）

2. Agent 经验（必须，但限制长度）
   - AerotriWeb_AGENT.md（最多 10KB）
   - 如果太长，只提供相关章节

3. 历史案例（可选，但推荐）
   - diagnosis_history.log（最近 3-5 条相似案例）
   - 根据任务类型和错误特征匹配

4. 系统经验（可选，复杂问题时提供）
   - CLAUDE.md（相关章节，如 "GPU 选择"）
   - 配置文件（如 settings.yaml）
```

---

## 🤖 交互设计

### 苏格拉底提问法（#24）

当 Agent 不确定时，主动提问：

```
我需要更多信息来诊断这个问题：

🔍 关于数据质量
1. 这些图片是从无人机采集的吗？
2. 飞行高度和重叠度是多少？
3. 地面纹理是否丰富（如城市、农田）？

🔍 关于环境
4. GPU 型号和显存大小？
5. CUDA 版本？

🔍 关于配置
6. 使用的是默认参数还是自定义参数？
7. 是否启用了分区模式？

请回答这些问题，我可以更准确地分析。
```

### 自动修复 vs 人工介入

**自动修复**（适用于明确的问题）:
- 相机模型不兼容 → 运行 undistortion
- 权限错误 → 修正权限
- 磁盘空间不足 → 清理临时文件

**人工介入**（适用于复杂问题）:
```
⚠️ 多次自动修复失败，建议人工介入。

这个问题可能是一个新的错误模式，不在已知知识库中。

下一步建议：
1. 查看完整日志：data/outputs/{block_id}/task.log
2. 在 GitHub Issues 中搜索类似问题
3. 联系开发者：@yourname

如果你解决了这个问题，请告诉我，我会更新知识库。
```

---

## 📊 可追溯性设计

### 三级追溯

1. **Block 级别**
   - 每个 Block 关联到诊断历史
   - 通过 Block ID 查询所有诊断记录

2. **错误模式级别**
   - 每个错误模式有历史案例列表
   - 通过错误类型查询所有相关 Block

3. **时间级别**
   - diagnosis_history.log 按时间排序
   - 可以按时间范围统计诊断趋势

### 统计与分析

```python
# 按错误类型统计
def get_error_type_stats():
    """
    返回：
    {
        "CUDA OOM": {"count": 10, "last_occurrence": "2025-02-09"},
        "Bundle Adjustment": {"count": 5, "last_occurrence": "2025-02-08"},
        ...
    }
    """

# 按算法统计
def get_algorithm_stats():
    """
    返回：
    {
        "COLMAP": {"failures": 20, "success_rate": 0.85},
        "GLOMAP": {"failures": 5, "success_rate": 0.95},
        ...
    }
    """

# 自动修复率
def get_auto_fix_stats():
    """
    返回：
    {
        "total_diagnoses": 50,
        "auto_fixed": 25,
        "auto_fix_rate": 0.5,
        "manual_intervention": 25
    }
    """
```

---

## 🚀 扩展方向

### 1. 智能相似度匹配

**现状**: 简单按任务类型匹配

**目标**: 使用 Embedding 模型计算相似度

```python
async def _find_similar_cases(self, context: Dict[str, Any], limit: int = 5):
    # 1. 提取当前错误的特征
    error_text = context.get('error_message', '')
    log_text = context.get('log_content', {}).get('main_log', '')

    # 2. 使用 Embedding 模型
    current_embedding = await embedding_model.encode(f"{error_text} {log_text}")

    # 3. 计算与历史案例的相似度
    similarities = []
    for case in history_cases:
        case_embedding = case.get('embedding')
        score = cosine_similarity(current_embedding, case_embedding)
        similarities.append((case, score))

    # 4. 返回最相似的 N 个
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:limit]
```

### 2. 多模态诊断

**现状**: 只分析文本日志

**目标**: 支持图片、截图

```python
async def collect_failure_context(self, block_id: int, ...):
    context = {
        # ... 现有字段 ...
        "screenshots": await self._collect_screenshots(block_id),
        "visualizations": await self._collect_visualizations(block_id),
    }
```

### 3. GitHub Issues 集成

**现状**: 只记录到本地

**目标**: 自动创建 GitHub Issue

```python
async def _update_knowledge_base(self, context, diagnosis, auto_fixed):
    # 如果是新问题且无法自动修复
    if diagnosis.get('is_new_pattern') and not auto_fixed:
        # 创建 GitHub Issue
        issue_url = await github_api.create_issue(
            title=f"自动诊断: {diagnosis.get('error_type')}",
            body=self._format_issue_body(context, diagnosis),
            labels=["diagnosis", "auto-generated", diagnosis.get('error_type')],
        )

        # 记录 Issue URL
        diagnosis['github_issue'] = issue_url
```

### 4. Web UI

**现状**: 只通过钉钉交互

**目标**: 提供 Web 界面

```
/diagnostics/{block_id}
├── 失败摘要
├── 错误分析（AI 生成）
├── 修复建议（可执行按钮）
├── 历史相似案例
└── 相关文档链接
```

---

## 📝 下一步行动

### Phase 1: 基础集成（1-2 天）

- [ ] 配置 OpenClaw Webhook URL
- [ ] 在 task_runner.py 中集成 `on_task_failure()`
- [ ] 测试诊断流程（手动触发）
- [ ] 验证知识库更新

### Phase 2: 完善知识库（3-5 天）

- [ ] 添加常见错误模式到 `AerotriWeb_AGENT.md`
  - CUDA OOM
  - Bundle Adjustment 失败
  - 相机模型不兼容
  - 磁盘空间不足
- [ ] 收集历史案例（从现有日志）
- [ ] 编写更多自动修复场景

### Phase 3: 增强功能（1-2 周）

- [ ] 实现智能相似度匹配
- [ ] 添加 Web UI
- [ ] 集成 GitHub Issues
- [ ] 添加诊断统计和可视化

### Phase 4: 优化与迭代（持续）

- [ ] 分析诊断准确率
- [ ] 收集用户反馈
- [ ] 优化 Prompt 质量
- [ ] 扩展知识库覆盖范围

---

## 🔗 相关资源

- [Vibe Coding 最佳实践](../Vibe Coding最佳实践.md)
- [CLAUDE.md](../CLAUDE.md)
- [诊断 Agent 使用指南](./ai-diagnostic-agent/README.md)
- [OpenClaw 文档](https://openclaw.example.com)

---

**作者**: Aerotri-Web Team
**更新时间**: 2025-02-09
**版本**: 1.0.0
