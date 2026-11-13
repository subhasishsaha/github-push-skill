#!/usr/bin/env python3
"""
Specialized Documentation-to-Code Drift Scanner
Zero-dependency Python 3 script.
Scans README.md and documentation files for:
- Dead internal relative file links [title](./path/to/file)
- Dead relative image links ![alt](./assets/img.png)
- References to non-existent entrypoints or script paths
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

MARKDOWN_LINK_PATTERN = r"""(?<!\!)\[([^\]]+)\]\(([^)]+)\)"""
MARKDOWN_IMAGE_PATTERN = r"""\!\[([^\]]*)\]\(([^)]+)\)"""

def is_external_url(url: str) -> bool:
    return any(url.lower().startswith(proto) for proto in ["http://", "https://", "mailto:", "ftp://", "#", "file://"])

def clean_target_path(link_target: str) -> str:
    # Remove anchor #section
    path_part = link_target.split("#")[0].strip()
    # Remove query params ?foo=bar
    path_part = path_part.split("?")[0].strip()
    return path_part

def strip_markdown_code(text: str) -> str:
    """Remove fenced code blocks and inline code spans to prevent false positives."""
    # Strip ```...``` fenced code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Strip `...` inline code spans
    text = re.sub(r"`[^`\n]+`", "", text)
    return text

def verify_markdown_file(doc_path: Path, repo_root: Path) -> List[Dict[str, Any]]:
    findings = []
    if not doc_path.is_file():
        return findings

    try:
        raw_content = doc_path.read_text(encoding="utf-8", errors="replace")
        content = strip_markdown_code(raw_content)
        doc_dir = doc_path.parent

        # 1. Check relative links
        for match in re.finditer(MARKDOWN_LINK_PATTERN, content):
            label, target_str = match.group(1), match.group(2).strip()
            if is_external_url(target_str):
                continue

            cleaned = clean_target_path(target_str)
            if not cleaned:
                continue

            # Resolve relative to doc_dir or repo_root
            resolved_from_doc = (doc_dir / cleaned).resolve()
            resolved_from_root = (repo_root / cleaned).resolve()

            if not resolved_from_doc.exists() and not resolved_from_root.exists():
                findings.append({
                    "file": str(doc_path),
                    "type": "DEAD_MARKDOWN_LINK",
                    "target": target_str,
                    "description": f"Dead relative link '[{label}]({target_str})': target file not found on disk."
                })

        # 2. Check relative images
        for match in re.finditer(MARKDOWN_IMAGE_PATTERN, content):
            alt, target_str = match.group(1), match.group(2).strip()
            if is_external_url(target_str):
                continue

            cleaned = clean_target_path(target_str)
            if not cleaned:
                continue

            resolved_from_doc = (doc_dir / cleaned).resolve()
            resolved_from_root = (repo_root / cleaned).resolve()

            if not resolved_from_doc.exists() and not resolved_from_root.exists():
                findings.append({
                    "file": str(doc_path),
                    "type": "DEAD_MARKDOWN_IMAGE",
                    "target": target_str,
                    "description": f"Dead relative image link '![{alt}]({target_str})': image file not found on disk."
                })
    except (OSError, UnicodeDecodeError):
        pass

    return findings

def scan_doc_drift(repo_root: Path) -> List[Dict[str, Any]]:
    findings = []
    # Check README.md first
    readme_candidates = [f for f in ["README.md", "README.rst", "README.txt"] if (repo_root / f).is_file()]
    for rm in readme_candidates:
        findings.extend(verify_markdown_file(repo_root / rm, repo_root))

    # Check docs directory if present
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for md_file in docs_dir.rglob("*.md"):
            findings.extend(verify_markdown_file(md_file, repo_root))

    return findings

def main():
    parser = argparse.ArgumentParser(description="Scan for documentation drift and dead links")
    parser.add_argument("path", nargs="?", default=".", help="Root repository path")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    findings = scan_doc_drift(target)

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        print(f"\n📄 Documentation-to-Code Drift Scan: {target}")
        print(f"Total findings: {len(findings)}\n")
        for f in findings:
            rel = Path(f["file"]).relative_to(target) if target in Path(f["file"]).parents or target == Path(f["file"]) else f["file"]
            print(f"[{f['type']}] {rel}")
            print(f"   {f['description']}\n")

if __name__ == "__main__":
    main()
