---
name: git-aerotri
description: Automated git workflow for the AeroTri-Web project with intelligent commit message generation, documentation updates, and code review. Use when working with the Aerotri-Web codebase for creating properly formatted git commits following project conventions, updating project documentation based on code changes, reviewing code for bugs and security issues, ensuring proper .gitignore configuration, and managing branches.
---

# Git-Aerotri

## Overview

Automated git workflow assistant for the AeroTri photogrammetry platform. Analyzes code changes, generates conventional commit messages with Chinese descriptions, updates project documentation, performs code review, and manages branches following project conventions.

## Quick Start

Basic workflow:
```bash
# 1. Generate diff and analyze
git diff > diff.txt

# 2. Review for issues
python3 scripts/review_code.py diff.txt

# 3. Generate commit message
python3 scripts/generate_commit_msg.py diff.txt

# 4. Update documentation (manual, based on analysis)
python3 scripts/analyze_diff.py diff.txt
```

## Workflow

### 1. Analyze Changes

Generate and analyze diff:
```bash
git diff > diff.txt
python3 /root/.claude/skills/git-aerotri/scripts/analyze_diff.py diff.txt
```

This categorizes changes by:
- **Backend changes**: API, models, services, config
- **Frontend changes**: components, views, types, API client
- **Documentation**: markdown files
- **Tests**: test files

### 2. Code Review

Check for bugs and security issues:
```bash
python3 /root/.claude/skills/git-aerotri/scripts/review_code.py diff.txt
```

Checks for:
- **Critical**: Command injection, SQL injection, XSS, eval/exec
- **Warning**: Bare except, missing context managers, debug prints
- **Info**: Missing docstrings, type checking disabled

### 3. Review Git Status

Check repository state:
```bash
git status
git branch -a
```

Determine if new branch needed based on changes.

### 4. Update .gitignore

Ensure intermediate files excluded:
- Build artifacts: `build/`, `dist/`, `__pycache__/`
- Dependencies: `node_modules/`, `venv/`
- Data/outputs: `aerotri-web/data/`
- Logs: `*.log`
- Test files: `*_test.py`, `test_*.py`

### 5. Update Documentation

Based on change categories:

**Backend changes** → Update:
- `CLAUDE.md`: API endpoints, services, models
- `aerotri-web/CLAUDE.md`: Architecture patterns

**Frontend changes** → Update:
- `CLAUDE.md`: Component list, views
- `aerotri-web/README.md`: Feature list

**Config changes** → Update:
- Both CLAUDE.md files: Environment variables
- Both README.md files: Configuration sections

**New features** → Update:
- All documentation: Feature descriptions, usage

### 6. Stage Files

Stage relevant changes:
```bash
# Add code changes
git add aerotri-web/backend/app/
git add aerotri-web/frontend/src/

# Add documentation
git add CLAUDE.md README.md
git add aerotri-web/CLAUDE.md aerotri-web/README.md

# Add config
git add .gitignore
```

### 7. Generate Commit Message

Generate commit message following project style:
```bash
python3 /root/.claude/skills/git-aerotri/scripts/generate_commit_msg.py diff.txt [branch_name]
```

Commit format:
```
<type>(<scope>): <description (Chinese)>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `perf`, `refactor`, `config`, `docs`, `chore`, `test`

Example:
```
feat: 添加 3D GS Tiles 转换功能

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 8. Commit

Create commit with generated message:
```bash
git commit -F <commit_message_file>
```

## Commit Message Types

| Type | Usage | Example |
|------|-------|---------|
| `feat` | New feature | `feat: 添加 3DGS Tiles 转换功能` |
| `fix` | Bug fix | `fix: 修复分区合并时数据丢失问题` |
| `perf` | Performance | `perf: 优化点云加载性能` |
| `refactor` | Refactoring | `refactor: 重构配置系统` |
| `config` | Configuration | `config: 更新算法路径配置` |
| `docs` | Documentation | `docs: 更新 README 文档` |
| `chore` | Maintenance | `chore: 添加 .gitignore 规则` |

## Documentation Files

Updates these files based on changes:

1. **`/root/work/Aerotri-Web/CLAUDE.md`** - Root project guide
2. **`/root/work/Aerotri-Web/README.md`** - Root project README (Chinese)
3. **`/root/work/Aerotri-Web/aerotri-web/CLAUDE.md`** - Web app architecture
4. **`/root/work/Aerotri-Web/aerotri-web/README.md`** - Web app README (Chinese)

## Branch Management

Check branches:
```bash
git branch -a  # List all branches
git branch -vv  # List with tracking info
```

Create feature branch when needed:
```bash
git checkout -b feature/descriptive-name
```

Push to remote:
```bash
git push -u origin feature/descriptive-name
```

## Resources

### scripts/

- **`analyze_diff.py`**: Categorizes changes by type (backend/frontend/config/docs)
- **`generate_commit_msg.py`**: Generates conventional commit messages with Chinese descriptions
- **`review_code.py`**: Checks for security issues, bugs, anti-patterns

### references/

- **`commit_style.md`**: Project commit message conventions and examples
- **`documentation_guide.md`**: Guidelines for updating documentation files

Read these references for detailed patterns when updating docs or commits.
