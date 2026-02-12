# 07-contribution

欢迎贡献到 AeroTri-Web 项目！

## 目录

- [如何贡献](#如何贡献)
- [代码规范](#代码规范)
- [Commit规范](#commit规范)
- [Pull Request流程](#pull-request流程)
- [问题报告](#问题报告)
- [开发环境](#开发环境)

---

## 如何贡献

我们欢迎所有形式的贡献！

### 贡献类型

**🐛 Bug修复**
- 报告明确的bug
- 提供复现步骤
- 包含错误日志
- 附上修复建议

**✨ 新功能**
- 提出新功能建议
- 描述使用场景
- 讨论实现方案

**📚 文档改进**
- 修正文档错误
- 补充缺失内容
- 改进文档结构
- 添加代码示例

**🔧 代码重构**
- 优化现有代码
- 提升代码可读性
- 改善性能
- 添加类型注解

**🌍 国际化**
- 添加多语言支持
- 改进翻译
- 适配本地化

---

## 代码规范

### Python规范（PEP 8）

**基本规则**：
- 使用4空格缩进（不使用Tab）
- 每行最大79字符（除注释）
- 导入顺序：标准库 → 第三方库 → 本地模块
- 类名使用PascalCase，函数/变量使用snake_case

**示例**：
```python
# ✅ 好的代码
from typing import Optional
from sqlalchemy import select

async def get_block(db: AsyncSession, block_id: str) -> Optional[Block]:
    """获取Block详情。"""
    result = await db.execute(
        select(Block).where(Block.id == block_id)
    )
    return result.scalar_one()
```

**类型注解**：
```python
# 明确类型注解
def process_block(block_id: str, params: dict) -> Block:
    pass

# 使用TypeChecking
from typing import List, Dict, Any
```

### TypeScript/Vue规范

**基本规则**：
- 使用2空格缩进
- 组件名使用PascalCase
- 文件名使用kebab-case或PascalCase
- 使用const/let而非var

**示例**：
```typescript
// ✅ 好的代码
import { ref, computed } from 'vue'

interface BlockData {
  id: string
  name: string
  status: BlockStatus
}

export const useBlockData = () => {
  const currentBlock = ref<BlockData | null>(null)

  const blockCount = computed(() =>
    currentBlock.value ? 1 : 0
  )

  function resetBlock() {
    currentBlock.value = null
  }

  return {
    currentBlock,
    blockCount,
    resetBlock
  }
}
```

**组件结构**：
```vue
<template>
  <div class="block-card">
    <h3>{{ block.name }}</h3>
    <p>Status: {{ block.status }}</p>
  </div>
</template>

<script setup lang="ts">
import { defineProps, computed } from 'vue'
import type { BlockData } from '@/types'

interface Props {
  block: BlockData
}

const props = defineProps<Props>()

const statusClass = computed(() => {
  switch (props.block.status) {
    case 'created': return 'status-created'
    case 'queued': return 'status-queued'
    case 'running': return 'status-running'
    case 'completed': return 'status-completed'
    case 'failed': return 'status-failed'
    case 'cancelled': return 'status-cancelled'
    default: return ''
  }
})
</script>

<style scoped>
.block-card {
  padding: 16px;
  border: 1px solid #e0e0;
  border-radius: 4px;
}

.status-created { background-color: #f0f0; }
.status-queued { background-color: #fff7e0; }
.status-running { background-color: #42b983; }
.status-completed { background-color: #66bb6a; }
.status-failed { background-color: #f44336; }
.status-cancelled { background-color: #9ca3af; }
</style>
```

---

## Commit规范

### Conventional Commits

**格式**：
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）**：
- `feat`: 新功能
- `fix`: Bug修复
- `perf`: 性能优化
- `refactor`: 代码重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具链更新
- `style`: 代码风格调整

**示例**：
```
feat(blocks): add partition support for large datasets

- Implement partition configuration panel
- Add partition service logic
- Update task runner to handle partitions
- Add partition status tracking

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Commit最佳实践

1. **标题**：
   - 使用原形中文描述
   - 简洁明了（不超过50字符）
   - 不使用句号结尾

2. **Body**：
   - 详细说明"为什么"和"如何"
   - 包含实现细节
   - 列出所有改动

3. **关联Issue**：
   - 在body末尾添加 `Closes #123` 或 `Fixes #456`
   - 自动关闭相关Issue

---

## Pull Request流程

### 1. Fork和克隆

```bash
# Fork项目到你的账号
git clone https://github.com/your-org/aerotri-web.git
cd aerotri-web
```

### 2. 创建分支

```bash
# 功能分支命名
git checkout -b feature/your-feature-name

# 修复分支命名
git checkout -b fix/issue-123-bug-description

# 文档分支命名
git checkout -b docs/update-api-guide
```

### 3. 开发和测试

**开发前检查**：
- [ ] 遵循代码规范
- [ ] 添加必要的测试
- [ ] 更新相关文档
- [ ] 确保代码通过linting
- [ ] 本地测试通过

### 4. 提交代码

```bash
# 提交到你的fork
git add .
git commit -m "feat: add your feature description"
```

### 5. 创建Pull Request

**PR标题**：
- 使用Conventional Commit格式
- 简洁描述

**PR描述模板**：
```markdown
## 变更说明
<!-- 简要描述这个PR做了什么 -->

## 变更类型
- [ ] 新功能 (feat)
- [ ] Bug修复 (fix)
- [ ] 性能优化 (perf)
- [ ] 代码重构 (refactor)
- [ ] 文档更新 (docs)
- [ ] 破坏性变更 (breaking change)

## 测试
- [ ] 单元测试已添加/更新
- [ ] 所有测试通过
- [ ] 本地测试环境：Python 3.10, Node.js 18

## 截图/演示（如适用）
<!-- 添加截图或GIF演示功能 -->

## Checklist
- [ ] 遵循代码规范
- [ ] 更新相关文档
- [ ] 添加/更新测试
- [ ] 无新增warnings

## 相关Issue
Closes #123
```

### PR命名规范

```yaml
命名格式：
  feat: 新功能
  fix: Bug修复
  perf: 性能优化
  refactor: 代码重构
  docs: 文档更新

分支命名：
  feature/功能名
  fix/issue号-简短描述
  hotfix/紧急修复
  release/版本号
```

---

## 问题报告

### Bug报告模板

**报告Issue前请检查**：
- [ ] 是否已有相同Issue
- [ ] Bug能否稳定复现
- [ ] 提供最小复现示例

**Issue模板**：
```markdown
### Bug描述
<!-- 清晰简洁地描述bug -->

**复现步骤**：
1. 步骤一
2. 步骤二
3. ...

**期望行为**：
<!-- 应该发生什么 -->

**实际行为**：
<!-- 实际发生了什么 -->

**环境信息**：
- AeroTri-Web版本：
- 操作系统：
- Python版本：
- Node.js版本：
- 浏览器版本：

**附加信息**：
<!-- 错误日志、截图等 -->
```

### 功能请求

**功能请求模板**：
```markdown
### 功能描述
<!-- 清晰描述你想要的功能 -->

**使用场景**：
<!-- 描述使用场景 -->

**可能的实现方案**：
<!-- 如果你有想法，可以分享 -->

**优先级**：
- [ ] 高优先级
- [ ] 中优先级
- [ ] 低优先级
```

---

## 开发环境

### 环境设置

**后端**：
```bash
cd aerotri-web/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**前端**：
```bash
cd aerotri-web/frontend
npm install
npm run dev
```

**代码风格检查**：
```bash
# 后端：Black格式化
black aerotri-web/backend/app

# 前端：ESLint检查
cd aerotri-web/frontend
npm run lint
```

**运行测试**：
```bash
# 后端测试
cd aerotri-web/backend
pytest

# 前端测试
cd aerotri-web/frontend
npm run test
```

### 调试配置

**VS Code配置（推荐）**：
```json
{
  "python.linting.enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenpjohnson.vscode-typescript-react"
  }
}
```

---

## 代码审查流程

### 提交前自查

- [ ] 代码符合规范
- [ ] 添加了必要的测试
- [ ] 更新了文档
- [ ] 无新增warnings
- [ ] 性能影响可接受
- [ ] 向后兼容

### 审查重点

1. **功能正确性**：是否实现了需求
2. **代码质量**：可读性、可维护性
3. **性能考虑**：是否有性能问题
4. **安全性**：是否有安全隐患
5. **测试覆盖**：是否有足够测试

### 反馈方式

**正面反馈**：
- 代码实现很好
- 只需小调整
- 学习了新技巧

**建设性反馈**：
- 指出具体问题
- 提供改进建议
- 帮助理解需求

---

## 社区准则

### 行为准则

- ✅ 尊重所有贡献者
- ✅ 建设性讨论
- ✅ 接受反馈和批评
- ❌ 禁止人身攻击
- ❌ 禁止骚扰行为

### 沟通指南

1. 使用英文进行沟通和讨论
2. Issue和PR使用英文描述
3. 保持耐心，等待维护者review
4. 遵循项目代码规范

---

## 获取帮助

### 沟通渠道

- **GitHub Issues**: 报告bug和功能请求
- **GitHub Discussions**: 技术讨论
- **Pull Request**: 代码审查和合并

### 联系维护者

**技术问题**：
- 提Issue并添加 `question` 标签
- 在Discussion中提问

**紧急问题**：
- 查看项目文档
- 搜索已有Issues

---

感谢你的贡献！让我们一起让AeroTri-Web变得更好！
