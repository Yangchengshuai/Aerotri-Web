# AI应用开发方法论 - 苏格拉底式对话总结

**日期**: 2026-02-24
**对话方式**: 苏格拉底提问法
**目标**: 探索如何更好地进行AI应用开发，达到95%自动化水平

---

## 一、核心认知与定位

### 1.1 AI应用的定义
> 充分借助 AI coding 及各种 AI 工具开发出来的 APP/工具，可以上线或开源

### 1.2 理想角色分配
- **AI (95%)**: 技术栈选择、代码开发、测试、部署、文档编写、市场调研、技术可行性分析、原型开发
- **人 (5%)**: 提供方向、寻找痛点、提供 taste、做选择、风险控制、用户体验验收

### 1.3 开发哲学
**Plan → Execute → Verify → Record → Abstract → Improve**

形成完整闭环，通过记忆系统实现复利迭代

---

## 二、现有工具生态

### 2.1 核心工具矩阵

| 工具 | 定位 | 核心优势 | 典型场景 | 协作方式 |
|------|------|----------|----------|----------|
| **Claude Code** | CLI开发工具 | 代码理解深、无需考虑交互 | 复杂功能开发、架构设计 | 通过claude-mem同步记忆 |
| **Cursor** | IDE工具 | 更好的交互和显示体验 | 快速编码、实时预览 | 手动切换 |
| **OpenClaw** | 本地AI Agent | 本地部署、操作本地数据、飞书集成 | 固定时间任务、内容创作、7x24交流 | 通过claude-mem检索历史 |
| **claude-mem** | 跨会话记忆系统 | 自动记录所有工具使用历史 | 解决工具切换时上下文丢失 | 作为记忆中枢 |

### 2.2 工具组合策略

#### 开发组合模式
- **规划阶段**: Claude Code + brainstorming skill
- **开发阶段**: Claude Code（方案） + Codex（精准编码）
- **调试阶段**: Codex（代码修复） + Chrome DevTools MCP（前端自测）
- **知识沉淀**: claude-mem自动记录 + OpenClaw文档生成

#### 记忆流转机制
```
Claude Code开发 → claude-mem记录 → OpenClaw检索 → 继承上下文
     ↑                                                              ↓
     └────────────────── lessons.md复利迭代 ←─────────────────────────┘
```

---

## 三、工作流演进史

### 3.1 第一阶段：手动Prompt（隐式工作流）
- 特点：全靠脑子里的经验，每次手动写prompt
- 问题：不可复制、不可追溯、难以改进

### 3.2 第二阶段：Superpower Skill（半显式）
- 特点：使用superpower的skill加强AI协作
- 问题：skill调用不够系统化，覆盖场景有限

### 3.3 第三阶段：CLAUDE.md工作流（显式化）
- 特点：完整的工作流程文档，每次会话自动加载
- 状态：**当前阶段，需要实践验证和持续优化**

---

## 四、当前工作流框架（CLAUDE.md）

### 4.1 Workflow Orchestration

#### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

#### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

#### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

#### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

#### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

#### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

### 4.2 Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

### 4.3 Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

## 五、关键Gap分析

### 5.1 前端自动化测试Gap

#### 当前问题
- playwright/agent browser在服务器中失败、慢、有网络问题
- Chrome DevTools MCP下载失败
- **核心问题**：手动触发，未形成自动化闭环

#### 理想流程
```
Claude Code修改前端代码
  → [自动触发] → Chrome DevTools MCP运行测试
    → [成功] → 标记完成
    → [失败] → 自动修复或升级给人
```

#### 关键问题
- **触发点**：代码修改后自动？手动调用skill？AI判断触发？
- **反馈点**：自动修复？报告给人？失败3次后谁来接管？

### 5.2 工具协作 vs 切换

#### 当前模式（切换）
```
你 → Claude Code: "重构数据库"
Claude Code: 写migration代码
你 → OpenClaw: "记录这次重构决策"
OpenClaw: "已记录到项目文档"
```

#### 理想模式（协作）
```
你 → Claude Code: "重构数据库"
Claude Code: "我先查claude-mem，看看OpenClaw之前记录的架构决策"
→ [自动] → Claude Code: "根据上次决策，这次改用PostgreSQL"
Claude Code: 写代码、测试、部署
→ [自动] → OpenClaw: "检测到代码变更，自动更新项目文档"
```

#### 协作本质
- **切换**：人手动连接工具，上下文靠claude-mem被动检索
- **协作**：工具主动调用，事件驱动，自动化流程

### 5.3 复利迭代的三个阶段

#### 第1阶段：记录
-犯错 → 手动记录到lessons.md ✅ **已实现**

#### 第2阶段：提醒
-类似场景 → AI主动提醒："根据lesson #12，这里应该..." ⚠️ **部分实现**（通过CLAUDE.md加载）

#### 第3阶段：内化
-AI直接不犯这个错 ❌ **未实现**

#### 真正的复利迭代
```
第1次犯错 → 记录到lessons.md
第2次类似场景 → AI主动提醒："根据lesson #12，这里应该..."
第3次 → AI直接不犯这个错
```

### 5.4 工作流的显式化程度

#### 关键检验标准
**如果让一个新来的AI接手你的项目，它能凭文档独立完成"写代码→测试→部署"吗？**

- **如果能** → 工作流是可复制的 ✅
- **如果不能** → 工作流还在脑子里 ❌

#### 当前状态评估
- CLAUDE.md已写好工作流规则 ✅
- 但实际执行度未知（着急时可能跳过plan）⚠️
- 自动化触发机制未建立 ❌

---

## 六、成本与ROI分析

### 6.1 时间成本对比

#### 手动模式（当前）
```
前端bug出现
→ 你复现问题
→ 复制错误信息
→ 喂给AI
→ 等待修复
→ 你再测试
```
**总耗时**: ~15分钟/次

#### 自动化模式（理想）
```
前端bug出现
→ AI自动检测
→ AI自动修复
→ AI自动验证
```
**总耗时**: ~3分钟/次

**节省**: 12分钟/次 = **80%时间节省**

### 6.2 模型成本对比

| 模型 | 成本 | 适合场景 |
|------|------|----------|
| **Haiku** | ~$0.25/1M tokens | 简单任务、快速迭代 |
| **Sonnet 4.5** | ~$3/1M tokens | 一般开发任务 |
| **Opus 4.6** | ~$15/1M tokens | 复杂架构设计、关键决策 |

### 6.3 成本优化策略

#### 分层使用模型
- **探索阶段**（调研、方案设计）: Opus（贵但聪明）
- **执行阶段**（写代码、测试）: Sonnet（性价比高）
- **简单任务**（格式化、文档生成）: Haiku（超便宜）

#### ROI计算
```
场景: 开发一个功能
- Sonnet: 500K tokens = $1.5
- Opus: 500K tokens = $7.5
- 差价: $6

但Opus可能:
- 减少debug时间: 30分钟
- 提高代码质量: 减少2次返工
- 你的时薪: $50/小时
- 节省价值: $25

ROI = ($25 - $6) / $6 = 317%
```

**结论**: 在关键环节使用顶级模型，ROI更高

---

## 七、从现状到95%自动化的路径

### 7.1 识别的障碍
1. ✅ **想法/创意**: 需要人提供方向和taste（已明确）
2. 🎯 **工作流完善**: 需要实践验证和自动化（**当前重点**）
3. ⚠️ **成本问题**: 可通过分层使用模型优化

### 7.2 本周行动计划（选B：工作流优化）

#### 目标
形成**质量监控、带记忆、不断复利进化的协作开发范式**

#### 具体步骤

**Step 1: 实践CLAUDE.md工作流**
- [ ] 下一个开发任务严格执行Plan Mode
- [ ] 使用Subagent Strategy并行处理
- [ ] 每次修正后更新lessons.md
- [ ] 验证完成度后再标记done

**Step 2: 建立自动化触发机制**
- [ ] 设计"前端代码修改后自动测试"的触发点
- [ ] 配置Chrome DevTools MCP自动调用
- [ ] 建立测试失败的反馈机制（自动修复 vs 升级给人）

**Step 3: 提升复利迭代效率**
- [ ] 将lessons.md从"加载"升级为"主动提醒"
- [ ] 设计规则让AI在类似场景自动应用lessons
- [ ] 追踪同一错误的重复率，验证内化程度

**Step 4: 工作流显式化检验**
- [ ] 写一个"新AI接手文档"，包含所有开发流程
- [ ] 测试：仅凭文档，AI能否独立完成"写代码→测试→部署"
- [ ] 补充缺失的文档和自动化脚本

**Step 5: 成本优化实验**
- [ ] 选一个小功能，分别用Sonnet和Opus开发
- [ ] 记录时间、成本、质量差异
- [ ] 计算ROI，形成模型选择指南

### 7.3 成功标准

#### 定量指标
- [ ] Plan Mode执行率 > 80%
- [ ] 前端bug自动化修复率 > 50%
- [ ] 同一错误重复率下降 > 30%
- [ ] 工作流显式化程度 > 90%

#### 定性指标
- [ ] AI能独立完成"开发→测试→部署"闭环
- [ ] lessons被主动应用而非被动加载
- [ ] 工具间从"切换"升级为"协作"
- [ ] 开发效率提升 > 2x

---

## 八、核心洞察总结

### 8.1 关于工具协作
**关键认知**: 工具之间不是"切换"关系，而是"协作"关系
- **切换**: 人手动连接，上下文靠记忆被动检索
- **协作**: 事件驱动，工具主动调用，自动化流程

### 8.2 关于工作流
**关键认知**: 写下来的工作流 ≠ 真正执行的工作流
- 需要通过实践验证AI是否遵守规则
- 需要建立自动化触发机制，而非依赖手动操作
- 需要检验工作流是否足够显式（新AI能否独立执行）

### 8.3 关于复利迭代
**关键认知**: 记录 → 提醒 → 内化，三个阶段逐级递进
- 第1阶段：记录到lessons.md ✅
- 第2阶段：AI主动提醒 ⚠️
- 第3阶段：AI直接不犯 ❌（终极目标）

### 8.4 关于角色定位
**关键认知**: 人的核心价值是"方向、痛点、taste、选择"
- 技术实现可以让AI做95%
- 但产品的"为什么做"、"做成什么样"必须人决定
- taste是主观判断，AI只能辅助不能替代

### 8.5 关于自动化路径
**关键认知**: 从现状到95%自动化，最大障碍是工作流
- 不是工具能力不够（已有Chrome DevTools MCP、claude-mem）
- 不是成本问题（可通过分层使用优化）
- **而是工作流不够自动化、不够显式、不够系统**

---

## 九、下一步行动

### 本周重点（工作流优化）
1. **实践CLAUDE.md工作流**，严格执行Plan Mode
2. **建立自动化触发机制**，从前端测试开始
3. **提升复利迭代效率**，从lessons提醒到内化
4. **工作流显式化检验**，让新AI能独立接手
5. **成本优化实验**，形成模型选择指南

### 长期目标（95%自动化）
- AI能独立完成：市场调研 → 技术选型 → 原型开发 → 代码实现 → 自动测试 → 部署上线 → 文档生成
- 人专注于：提供方向、寻找痛点、把控taste、做最终选择

---

## 十、关键文档索引

### 10.1 核心文档
- `CLAUDE.md`: AI协作工作流规则（每次会话自动加载）
- `tasks/lessons.md`: 复利迭代经验库（动态更新）
- `tasks/todo.md`: 任务跟踪与计划（可勾选项）

### 10.2 相关项目
- **Aerotri-Web**: 使用Cursor + Claude Code开发的Web项目
- **OpenClaw**: 本地AI Agent助手，支持飞书集成
- **Remotion视频项目**: AI辅助视频内容创作工作流

---

## 附录：苏格拉底式对话的价值

通过这次苏格拉底式对话，我们发现：

1. **问题不是工具，而是工作流**
   - 已有Chrome DevTools MCP但未自动化
   - 已有claude-mem但未主动协作
   - 已有CLAUDE.md但未严格执行

2. **真正的瓶颈在认知层面**
   - 认为工具间只能"切换"而非"协作"
   - 认为工作流"写下来"就是"显式化"
   - 认为成本是障碍而未计算ROI

3. **解决方案清晰可执行**
   - 本周聚焦工作流优化（选B）
   - 5个具体步骤，有成功标准
   - 形成可复制的开发范式

---

**文档版本**: v1.0
**最后更新**: 2026-02-24
**下次review**: 实践一周后，根据实际效果调整
