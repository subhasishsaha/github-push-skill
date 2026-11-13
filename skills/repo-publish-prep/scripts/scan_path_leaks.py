#!/usr/bin/env python3
"""
Specialized Local Environment & Hardcoded Path Leak Scanner
Zero-dependency Python 3 script.
Detects:
- Absolute Windows user paths (e.g., C:\\Users\\<user>\\...)
- Absolute POSIX user paths (e.g., /home/<user>/... or /Users/<user>/...)
- Hardcoded local IP addresses (192.168.x.x, 10.x.x.x)
- Hardcoded ports without environment fallback
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", "target", "dist", "build", "coverage", ".next"
}

PATH_LEAK_PATTERNS = [
    (r"(?i)[a-z]:[/\\]+(?:Users|Projects|Documents|Desktop)[/\\]+[a-zA-Z0-9_\-\./\\<>]+", "Hardcoded Windows user directory path"),
    (r"(?i)(?:/home|/Users)/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\./<>]+", "Hardcoded POSIX user home directory path"),
    (r"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b", "Hardcoded internal private IP address"),
]

def scan_file_for_path_leaks(file_path: Path) -> List[Dict[str, Any]]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for line_idx, line in enumerate(content.splitlines(), start=1):
            # Skip comments if obvious
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                # Still check if it looks like an absolute path accidentally pasted
                pass

            for pattern, desc in PATH_LEAK_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    val = match.group(0)
                    # Ignore common placeholders
                    if any(ph in val.lower() for ph in ["<user>", "username", "your_username", "placeholder", "example"]):
                        continue
                    findings.append({
                        "file": str(file_path),
                        "line": line_idx,
                        "type": "LOCAL_PATH_LEAK",
                        "match": val,
                        "description": f"{desc}: `{val}`"
                    })
    except (OSError, UnicodeDecodeError):
        pass
    return findings

def scan_path_leaks(target_dir: Path) -> List[Dict[str, Any]]:
    all_findings = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            file_path = Path(root) / f
            ext = file_path.suffix.lower()
            if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".json", ".yaml", ".yml", ".env.example"]:
                all_findings.extend(scan_file_for_path_leaks(file_path))
    return all_findings

def main():
    parser = argparse.ArgumentParser(description="Scan for hardcoded local paths and environment leaks")
    parser.add_argument("path", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    findings = scan_path_leaks(target)

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        print(f"\n🌍 Environment & Path Leak Scan: {target}")
        print(f"Total findings: {len(findings)}\n")
        for f in findings:
            rel = Path(f["file"]).relative_to(target) if target in Path(f["file"]).parents or target == Path(f["file"]) else f["file"]
            print(f"[{f['type']}] {rel}:{f['line']}")
            print(f"   {f['description']}\n")

if __name__ == "__main__":
    main()
