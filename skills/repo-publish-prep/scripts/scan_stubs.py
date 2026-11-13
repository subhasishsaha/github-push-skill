#!/usr/bin/env python3
"""
Specialized Stub, Mock, and Eagerness Bias Scanner
Zero-dependency Python 3 script.
Detects:
- Python AST: empty functions (pass / ...), raise NotImplementedError, empty except blocks
- Generic: TODO/FIXME comments, explicit not-implemented errors, empty catch blocks, mock returns
"""

import os
import ast
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

GENERIC_STUB_PATTERNS = [
    (r"(?i)(?://|#)\s*(?:TODO|FIXME|HACK|XXX)\b:?\s*(.*)", "Unresolved TODO/FIXME comment"),
    (r"(?i)throw\s+new\s+Error\(['\"][^'\"]*not\s+implemented[^'\"]*['\"]\)", "Explicit Not-Implemented error thrown"),
    (r"(?i)catch\s*\([^)]*\)\s*\{\s*\}", "Empty exception handler (silent error swallowing)"),
    (r"(?i)return\s+null;\s*//\s*(?:todo|temp|mock|stub)", "Hollow mock return value"),
    (r"(?i)return\s+undefined;\s*//\s*(?:todo|temp|mock|stub)", "Hollow mock return value"),
]

def scan_python_ast(file_path: Path) -> List[Dict[str, Any]]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return findings

    for node in ast.walk(tree):
        # 1. Functions whose entire body is just `pass` or `...`
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if body is just docstring + pass, or just pass
            real_body = [stmt for stmt in node.body if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str))]
            if len(real_body) == 1:
                stmt = real_body[0]
                if isinstance(stmt, ast.Pass):
                    findings.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "EMPTY_FUNCTION_PASS",
                        "name": node.name,
                        "description": f"Function '{node.name}' has no implementation (body is only 'pass')."
                    })
                elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
                    findings.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "EMPTY_FUNCTION_ELLIPSIS",
                        "name": node.name,
                        "description": f"Function '{node.name}' has no implementation (body is only '...')."
                    })
                elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call) and getattr(stmt.exc.func, "id", None) == "NotImplementedError":
                    findings.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "NOT_IMPLEMENTED_ERROR",
                        "name": node.name,
                        "description": f"Function '{node.name}' raises NotImplementedError."
                    })

        # 2. Empty except blocks swallowing broad exceptions
        if isinstance(node, ast.ExceptHandler):
            real_body = [stmt for stmt in node.body if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))]
            if len(real_body) == 1 and isinstance(real_body[0], ast.Pass):
                exc_name = getattr(node.type, "id", None)
                if node.type is None or exc_name in ["Exception", "BaseException"]:
                    findings.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "SILENT_EXCEPTION_SWALLOW",
                        "name": exc_name or "bare except",
                        "description": f"Broad except block silently swallows exceptions with 'pass'."
                    })

    return findings

def scan_text_patterns(file_path: Path) -> List[Dict[str, Any]]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for line_idx, line in enumerate(content.splitlines(), start=1):
            for pattern, desc in GENERIC_STUB_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    detail = match.group(1).strip() if match.groups() else ""
                    findings.append({
                        "file": str(file_path),
                        "line": line_idx,
                        "type": "STUB_PATTERN",
                        "name": line.strip()[:60],
                        "description": f"{desc}: {detail}" if detail else desc
                    })
    except (OSError, UnicodeDecodeError):
        pass
    return findings

def scan_stubs(target_dir: Path) -> List[Dict[str, Any]]:
    all_findings = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            file_path = Path(root) / f
            ext = file_path.suffix.lower()

            if ext == ".py":
                all_findings.extend(scan_python_ast(file_path))
                all_findings.extend(scan_text_patterns(file_path))
            elif ext in [".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp"]:
                all_findings.extend(scan_text_patterns(file_path))

    return all_findings

def main():
    parser = argparse.ArgumentParser(description="Scan for stubs, unimplemented functions, and eagerness bias")
    parser.add_argument("path", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    findings = scan_stubs(target)

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        print(f"\n🔍 Stub & Eagerness Bias Scan: {target}")
        print(f"Total findings: {len(findings)}\n")
        for f in findings:
            rel = Path(f["file"]).relative_to(target) if target in Path(f["file"]).parents or target == Path(f["file"]) else f["file"]
            print(f"[{f['type']}] {rel}:{f['line']}")
            print(f"   {f['description']}\n")

if __name__ == "__main__":
    main()
