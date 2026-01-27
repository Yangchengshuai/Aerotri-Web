#!/usr/bin/env python3
"""
Analyze git diff and extract structured information for documentation updates.

This script parses git diff output to identify:
- Modified files by type (backend/frontend/config)
- Added/removed features
- API changes
- Configuration changes
- Bug fixes
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Set


def parse_diff(diff_text: str) -> Dict[str, List[str]]:
    """Parse git diff output and categorize changes."""
    changes = {
        "backend": [],
        "frontend": [],
        "config": [],
        "docs": [],
        "tests": [],
        "other": []
    }

    # Track files that were modified
    modified_files = set()

    for line in diff_text.split('\n'):
        # Match diff file headers
        # Format: diff --git a/path/to/file b/path/to/file
        if line.startswith('diff --git'):
            # Extract the second file path (after " b/")
            parts = line.split()
            if len(parts) >= 4:
                file_path = parts[3][2:]  # Remove "b/" prefix
                modified_files.add(file_path)

    # Categorize files
    for file_path in modified_files:
        if file_path.startswith('aerotri-web/backend/'):
            if 'app/api/' in file_path:
                changes["backend"].append(("API", file_path))
            elif 'app/models/' in file_path:
                changes["backend"].append(("Model", file_path))
            elif 'app/services/' in file_path:
                changes["backend"].append(("Service", file_path))
            elif 'config/' in file_path:
                changes["config"].append(file_path)
            else:
                changes["backend"].append(("Other", file_path))
        elif file_path.startswith('aerotri-web/frontend/'):
            if 'src/api/' in file_path:
                changes["frontend"].append(("API", file_path))
            elif 'src/types/' in file_path:
                changes["frontend"].append(("Types", file_path))
            elif 'src/components/' in file_path:
                changes["frontend"].append(("Component", file_path))
            elif 'src/views/' in file_path:
                changes["frontend"].append(("View", file_path))
            else:
                changes["frontend"].append(("Other", file_path))
        elif file_path.endswith('.md'):
            changes["docs"].append(file_path)
        elif file_path.endswith(('_test.py', 'test_', '.spec.ts')):
            changes["tests"].append(file_path)
        else:
            changes["other"].append(file_path)

    return changes


def detect_feature_changes(diff_text: str) -> List[str]:
    """Detect potential feature additions from diff content."""
    features = []
    # Look for common patterns indicating new features
    patterns = [
        r'\+def (new_|create_|add_)\w+',
        r'\+async def (new_|create_|add_)\w+',
        r'\+POST /api/',
        r'\+GET /api/',
        r'\+@router\.',
        r'class \w+Block',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, diff_text)
        features.extend(matches)

    return features


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: analyze_diff.py <diff_file>")
        sys.exit(1)

    diff_file = Path(sys.argv[1])
    if not diff_file.exists():
        print(f"Error: Diff file not found: {diff_file}")
        sys.exit(1)

    diff_text = diff_file.read_text()

    # Analyze changes
    changes = parse_diff(diff_text)
    features = detect_feature_changes(diff_text)

    # Print summary
    print("=" * 60)
    print("DIFF ANALYSIS SUMMARY")
    print("=" * 60)

    for category, files in changes.items():
        if files:
            print(f"\n{category.upper()} ({len(files)} files):")
            for item in files:
                if isinstance(item, tuple):
                    print(f"  [{item[0]}] {item[1]}")
                else:
                    print(f"  {item}")

    if features:
        print(f"\nPOTENTIAL NEW FEATURES ({len(features)}):")
        for feature in features[:10]:  # Show first 10
            print(f"  - {feature}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
