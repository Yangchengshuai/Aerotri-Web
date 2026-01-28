# Claude Code Skills

本目录包含 AeroTri 项目的 Claude Code 技能（Skills），用于在不同服务器间共享和使用自动化工作流。

## 目录结构

```
.claude/skills/
├── git-aerotri/          # AeroTri 项目自动化 git 工作流
├── algorithmic-art/      # 算法艺术生成
├── brand-guidelines/     # 品牌设计规范
├── canvas-design/        # 视觉艺术设计
├── doc-coauthoring/      # 文档协作工作流
├── docx/                 # Word 文档处理
├── frontend-design/      # 前端界面设计
├── internal-comms/       # 内部通信模板
├── mcp-builder/          # MCP 服务器构建工具
├── pdf/                  # PDF 文档处理
├── pptx/                 # PowerPoint 演示文稿处理
├── skill-creator/        # 技能创建工具
├── slack-gif-creator/    # Slack GIF 制作
├── template/             # 技能模板
├── theme-factory/        # 主题样式工具
├── web-artifacts-builder/# Web 工件构建
├── webapp-testing/       # Web 应用测试
└── xlsx/                 # Excel 表格处理
```

## 克隆到其他服务器

当你在其他服务器上 clone 此仓库后，skills 会自动包含在 `.claude/skills/` 目录中。

### 使用 Skills

有两种方式使用这些 skills：

#### 方式 1: 通过 Claude Code CLI

Claude Code 会自动识别项目中的 skills 目录。当你运行 Claude Code 时，这些技能会自动可用。

```bash
cd /path/to/Aerotri-Web
claude
```

然后直接使用 skill：
```
/git-aerotri
```

#### 方式 2: 手动加载

如果你想在其他位置使用这些 skills，可以复制整个 skills 目录：

```bash
# 复制到其他项目的 claude 目录
cp -r /path/to/Aerotri-Web/.claude/skills /other/project/.claude/
```

## 核心技能：git-aerotri

`git-aerotri` 是专为 AeroTri 项目定制的 git 工作流助手。

### 功能

- **分析代码变更**：自动分类后端、前端、配置、文档变更
- **代码审查**：检查安全漏洞、bug 和代码规范
- **生成提交信息**：遵循项目规范的中文提交信息
- **更新文档**：根据代码变更自动更新 CLAUDE.md、README.md 等

### 使用示例

```bash
# 在 Claude Code 中
/git-aerotri

# 系统会自动：
# 1. 分析 git diff
# 2. 进行代码审查
# 3. 生成规范的 commit message
# 4. 更新相关文档
# 5. 执行 git commit
```

### 工作流程

1. **分析变更**：运行 `analyze_diff.py` 分类代码变更
2. **代码审查**：运行 `review_code.py` 检查安全问题
3. **生成提交信息**：运行 `generate_commit_msg.py` 创建中文提交信息
4. **更新文档**：根据变更类型更新相关文档
5. **提交**：使用生成的提交信息创建 git commit

### 提交信息格式

```
<type>(<scope>): <description (中文)>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `perf`: 性能优化
- `refactor`: 代码重构
- `config`: 配置更改
- `docs`: 文档更新
- `chore`: 维护任务
- `test`: 测试相关

## 其他技能

### 文档处理

- **docx**: Word 文档创建、编辑、跟踪更改
- **pptx**: PowerPoint 演示文稿处理
- **pdf**: PDF 表单填写、文本提取、合并/拆分
- **xlsx**: Excel 表格处理，支持公式和数据分析

### 设计相关

- **algorithmic-art**: 使用 p5.js 创建算法艺术
- **canvas-design**: 视觉艺术和海报设计
- **frontend-design**: 高质量前端界面设计
- **theme-factory**: 主题样式工具包
- **brand-guidelines**: Anthropic 品牌规范

### 开发工具

- **skill-creator**: 创建新的 Claude Code 技能
- **mcp-builder**: 构建 MCP (Model Context Protocol) 服务器
- **webapp-testing**: 使用 Playwright 进行 Web 应用测试
- **web-artifacts-builder**: 构建复杂的 HTML 工件

### 通信工具

- **internal-comms**: 内部通信模板（状态报告、更新等）
- **slack-gif-creator**: 创建优化的 Slack GIF

## 在 CI/CD 中使用

可以在 CI/CD 流程中使用这些技能：

```bash
# 示例：在 CI 中使用 git-aerotri
- name: Run git-aerotri workflow
  run: |
    git diff > diff.txt
    python3 .claude/skills/git-aerotri/scripts/analyze_diff.py diff.txt
    python3 .claude/skills/git-aerotri/scripts/review_code.py diff.txt
```

## 更新 Skills

如果你修改了某个 skill，记得提交更改：

```bash
git add .claude/skills/
git commit -m "chore: 更新 git-aerotri skill"
git push
```

## 创建新技能

使用 `skill-creator` 技能创建新的自定义技能：

```bash
/skill-creator
```

这会引导你完成技能创建流程，包括：
- 初始化技能结构
- 编写 SKILL.md 说明文档
- 添加必要的脚本和资源
- 打包技能以便共享

## 许可证

这些技能遵循各自的 LICENSE 文件：
- 大部分技能使用 MIT 许可证
- 请参考每个技能目录下的 LICENSE.txt 文件

## 联系方式

如有问题或建议，请通过项目仓库提 Issue。
