# Git Commit Message Style Guide

## Commit Message Format

This project follows conventional commit format with Chinese descriptions:

```
<type>(<scope>): <description>

[optional body]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Commit Types

| Type | Description | Examples |
|------|-------------|----------|
| `feat` | New feature | `feat: 添加 3DGS Tiles 转换功能` |
| `fix` | Bug fix | `fix: 修复分区合并时 2D points 数据丢失问题` |
| `perf` | Performance improvement | `perf: 优化点云加载性能` |
| `refactor` | Code refactoring | `refactor: 重构配置系统` |
| `config` | Configuration changes | `config: 更新算法路径配置为本地构建路径` |
| `docs` | Documentation updates | `docs: 更新 README 文档` |
| `chore` | Maintenance tasks | `chore: 更新依赖版本` |
| `test` | Test additions/changes | `test: 添加 API 单元测试` |

## Scopes

Commonly used scopes:
- `(backend)` - Backend changes
- `(frontend)` - Frontend changes
- `(api)` - API endpoints
- `(services)` - Service layer
- `(models)` - Data models
- `(config)` - Configuration

## Examples from Project History

```
feat: 添加 3D GS Tiles 转换功能
feat(frontend): 优化 3D 查看器交互体验和布局
fix: 修复相机重投影误差计算问题
perf(frontend): 优化 SplitCesiumViewer 高度显示
perf: 优化 BrushCompareViewer 使用单 viewer + splitDirection 实现分屏
config: 更新算法路径配置为本地构建路径
feat(aerotri-web): document recon version APIs
chore: 添加缺失的子模块配置到 .gitmodules
chore(deps): 添加 SPZ 点云压缩库作为子模块
```

## Writing Good Commit Messages

1. **Use imperative mood** in Chinese (e.g., "添加" not "添加了")
2. **Keep it concise** - under 50 characters for the title
3. **Focus on "why"** not "what" - explain the reasoning
4. **Capitalize first letter** of description
5. **No period** at the end of the title
6. **Include scope** for large changes
7. **Always add Co-Authored-By trailer** for Claude-generated commits
