#!/usr/bin/env python3
"""
Generate conventional commit message from git diff.

Analyzes git diff to generate commit messages following the project's style:
- feat: New feature
- fix: Bug fix
- config: Configuration changes
- chore: Maintenance tasks
- docs: Documentation updates
- perf: Performance improvements
- refactor: Code refactoring
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple


# Commit message patterns based on project history
COMMIT_PATTERNS = {
    "feat": [
        (r"添加|新增|增加|实现|集成|支持", "new feature"),
        (r"@router\.post\(|def (create|add|new)_", "API endpoint"),
        (r"3DGS|3D Tiles|OpenMVS|GLOMAP|COLMAP", "algorithm feature"),
        (r"Vue|Component|View", "frontend feature"),
    ],
    "fix": [
        (r"修复|解决|bug", "bug fix"),
        (r"异常|错误|失败", "error handling"),
        (r"overflow|溢出", "overflow fix"),
    ],
    "perf": [
        (r"优化|提升|改进|加速", "performance"),
        (r"性能|速度", "performance improvement"),
    ],
    "refactor": [
        (r"重构|改造|迁移", "refactoring"),
        (r"统一|标准化", "standardization"),
    ],
    "config": [
        (r"配置|路径|环境变量", "configuration"),
        (r"settings\.yaml|\.env", "config file"),
    ],
    "docs": [
        (r"文档|说明|README", "documentation"),
        (r"CLAUDE\.md|\.md:", "docs update"),
    ],
    "chore": [
        (r"删除|移除|清理", "cleanup"),
        (r"更新|升级|依赖", "maintenance"),
        (r"\.gitignore|\.gitmodules", "git maintenance"),
    ],
}


def analyze_diff(diff_text: str) -> Tuple[str, List[str], List[str]]:
    """Analyze diff and determine commit type, scope, and keywords."""
    lines = diff_text.split('\n')

    # Count changes by type
    type_scores = {commit_type: 0 for commit_type in COMMIT_PATTERNS.keys()}
    keywords = set()
    scopes = set()

    for line in lines:
        # Only look at added lines (start with +, but not +++ which is file header)
        if not line.startswith('+') or line.startswith('+++'):
            continue

        # Remove the + prefix
        content = line[1:].strip()

        # Check against patterns
        for commit_type, patterns in COMMIT_PATTERNS.items():
            for pattern, description in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    type_scores[commit_type] += 1
                    keywords.add(description)

        # Detect scope from file paths
        if 'backend/app/api/' in content:
            scopes.add("backend(api)")
        elif 'backend/app/services/' in content:
            scopes.add("backend(services)")
        elif 'frontend/src/' in content:
            scopes.add("frontend")
        elif 'config/' in content:
            scopes.add("config")
        elif '.py:' in content:
            scopes.add("backend")
        elif '.vue:' in content or '.ts:' in content:
            scopes.add("frontend")

    # Determine commit type (highest score)
    commit_type = max(type_scores.items(), key=lambda x: x[1])[0]

    # Special case: if only docs changed, use docs type
    if type_scores["docs"] > 0 and sum(type_scores.values()) == type_scores["docs"]:
        commit_type = "docs"

    return commit_type, list(scopes), list(keywords)


def generate_message(diff_text: str, branch: str = None) -> str:
    """Generate commit message from diff."""
    commit_type, scopes, keywords = analyze_diff(diff_text)

    # Build message
    if scopes:
        scope = f"({scopes[0]})"
    else:
        scope = ""

    # Get primary keywords
    primary_keywords = [k for k in keywords if len(k) > 3][:3]
    if primary_keywords:
        description = "、".join(primary_keywords[:2])
    else:
        description = "update code"

    # Create Chinese description based on type
    type_descriptions = {
        "feat": f"添加 {description}" if description else "新功能",
        "fix": f"修复 {description}" if description else "修复问题",
        "perf": f"优化 {description}" if description else "性能优化",
        "refactor": f"重构 {description}" if description else "代码重构",
        "config": f"更新 {description}" if description else "配置更新",
        "docs": f"更新文档: {description}" if description else "文档更新",
        "chore": f"{description}" if description else "维护任务",
    }

    title = f"{commit_type}{scope}: {type_descriptions.get(commit_type, 'update')}"

    # Add branch context if provided
    if branch and branch != "master" and branch != "main":
        title = f"[{branch}] {title}"

    return title


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: generate_commit_msg.py <diff_file> [branch_name]")
        sys.exit(1)

    diff_file = Path(sys.argv[1])
    if not diff_file.exists():
        print(f"Error: Diff file not found: {diff_file}")
        sys.exit(1)

    branch = sys.argv[2] if len(sys.argv) > 2 else None

    diff_text = diff_file.read_text()

    # Generate commit message
    commit_msg = generate_message(diff_text, branch)

    # Also add Co-Authored-By trailer
    full_message = f"""{commit_msg}

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"""

    print(full_message)


if __name__ == "__main__":
    main()
