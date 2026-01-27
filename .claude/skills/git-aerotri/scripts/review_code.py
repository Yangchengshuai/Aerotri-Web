#!/usr/bin/env python3
"""
Review code changes for common issues and bugs.

This script analyzes git diff for:
- Security issues (SQL injection, XSS, command injection)
- Error handling problems
- Resource leaks
- Type errors
- Common Python/JavaScript bugs
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple


# Security and bug patterns
ISSUES = {
    "critical": [
        (r"execute\([^)]*\+", "Command injection risk: string concatenation in execute()"),
        (r"os\.system\(|subprocess\.call\(|subprocess\.Popen\(", "System command execution: verify input sanitization"),
        (r"sql.*\+.*%s", "Potential SQL injection: string concatenation in SQL"),
        (r"\.innerHTML\s*=", "XSS risk: direct innerHTML assignment with user input"),
        (r"eval\(|exec\(", "Dangerous eval/exec: code injection risk"),
    ],
    "warning": [
        (r"except:", "Bare except: catches all exceptions including SystemExit"),
        (r"open\(.+\)\.read\(\)", "File opened without context manager (use 'with' statement)"),
        (r"\.close\(\)", "Manual close(): prefer context managers"),
        (r"TODO|FIXME|XXX|HACK", "Unresolved comment marker"),
        (r"print\(", "Debug print statement should be removed"),
    ],
    "info": [
        (r"def \w+\([^)]*\):\s*$", "Function without docstring"),
        (r"class \w+:\s*$", "Class without docstring"),
        (r"# type: ignore", "Type checking disabled"),
        (r"any\(|all\(", "Consider using any/all for readability"),
    ],
}


def analyze_line(line: str, line_num: int, file_path: str) -> List[Tuple[str, str, int]]:
    """Analyze a single line for issues."""
    found_issues = []

    # Check each pattern
    for severity, patterns in ISSUES.items():
        for pattern, message in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                found_issues.append((severity, message, line_num))

    return found_issues


def analyze_diff(diff_text: str) -> List[Tuple[str, str, int, str]]:
    """Analyze diff for code issues."""
    issues_found = []
    lines = diff_text.split('\n')

    current_file = None
    line_offset = 0

    for i, line in enumerate(lines):
        # Track file changes
        if line.startswith('+++ b/'):
            current_file = line[6:]
            line_offset = 0
            continue

        # Track hunk headers for line numbers
        if line.startswith('@@'):
            match = re.search(r'\+(\d+)', line)
            if match:
                line_offset = int(match.group(1)) - 1
            continue

        # Only analyze added lines
        if not line.startswith('+') or line.startswith('+++'):
            continue

        if line.startswith('+'):
            line_offset += 1

        # Analyze the line
        line_issues = analyze_line(line[1:], line_offset, current_file or "unknown")
        for severity, message, line_num in line_issues:
            issues_found.append((severity, message, line_num, current_file or "unknown"))

    return issues_found


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: review_code.py <diff_file>")
        sys.exit(1)

    diff_file = Path(sys.argv[1])
    if not diff_file.exists():
        print(f"Error: Diff file not found: {diff_file}")
        sys.exit(1)

    diff_text = diff_file.read_text()

    # Analyze for issues
    issues = analyze_diff(diff_text)

    if not issues:
        print("✅ No obvious issues found in the changes.")
        return 0

    # Group by severity
    by_severity = {"critical": [], "warning": [], "info": []}
    for severity, message, line_num, file_path in issues:
        by_severity[severity].append((message, line_num, file_path))

    # Print results
    for severity in ["critical", "warning", "info"]:
        items = by_severity[severity]
        if not items:
            continue

        icon = {"critical": "🔴", "warning": "⚠️", "info": "ℹ️"}[severity]
        print(f"\n{icon} {severity.upper()} ({len(items)} issues):")

        for message, line_num, file_path in items[:10]:  # Limit to 10 per severity
            print(f"  {file_path}:{line_num} - {message}")

        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more")

    # Return exit code based on critical issues
    if by_severity["critical"]:
        print("\n❌ Critical issues found! Please review before committing.")
        return 1
    elif by_severity["warning"]:
        print("\n⚠️ Warnings found. Review recommended.")
        return 0
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
