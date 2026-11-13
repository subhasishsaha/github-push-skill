#!/usr/bin/env python3
"""
Specialized Dependency Mismatch & Phantom Package Scanner
Zero-dependency Python 3 script.
Scans source code for imports and verifies them against manifest files
(package.json, requirements.txt, pyproject.toml).
Identifies undeclared packages and phantom dependencies.
"""

import os
import ast
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Set, Dict, List, Any

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", "target", "dist", "build", "coverage", ".next", ".turbo"
}

NODE_BUILTINS = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console",
    "constants", "crypto", "dgram", "diagnostics_channel", "dns", "domain",
    "events", "fs", "fs/promises", "http", "http2", "https", "inspector",
    "module", "net", "os", "path", "path/posix", "path/win32", "perf_hooks",
    "process", "punycode", "querystring", "readline", "repl", "stream",
    "stream/consumers", "stream/promises", "stream/web", "string_decoder",
    "test", "timers", "timers/promises", "tls", "trace_events", "tty",
    "url", "util", "util/types", "v8", "vm", "wasi", "worker_threads", "zlib"
}

def get_python_stdlib() -> Set[str]:
    # Python 3.10+ has sys.stdlib_module_names
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names)
    # Fallback standard library set
    return {
        "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib",
        "copy", "csv", "datetime", "decimal", "difflib", "email", "enum", "errno",
        "fnmatch", "functools", "glob", "gzip", "hashlib", "hmac", "html", "http",
        "importlib", "inspect", "io", "itertools", "json", "logging", "math",
        "multiprocessing", "os", "pathlib", "pickle", "platform", "pprint", "queue",
        "random", "re", "shutil", "signal", "socket", "sqlite3", "ssl", "stat",
        "string", "subprocess", "sys", "tempfile", "threading", "time", "traceback",
        "typing", "unittest", "urllib", "uuid", "warnings", "weakref", "zipfile"
    }

def scan_python_imports(file_path: Path) -> Set[str]:
    imports = set()
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_pkg = alias.name.split(".")[0]
                imports.add(top_pkg)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                top_pkg = node.module.split(".")[0]
                imports.add(top_pkg)
    return imports

def scan_js_imports(file_path: Path) -> Set[str]:
    imports = set()
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        # Match import ... from 'pkg' and import('pkg') and require('pkg')
        patterns = [
            r"""import\s+(?:[^"'\n]+\s+from\s+)?['"]([^"']+)['"]""",
            r"""require\s*\(\s*['"]([^"']+)['"]\s*\)""",
            r"""import\s*\(\s*['"]([^"']+)['"]\s*\)""",
        ]
        for p in patterns:
            for match in re.finditer(p, content):
                spec = match.group(1).strip()
                # Skip relative or absolute paths
                if spec.startswith(".") or spec.startswith("/") or spec.startswith("\\"):
                    continue
                # Handle scoped packages @org/pkg
                if spec.startswith("@"):
                    parts = spec.split("/")
                    pkg_name = f"{parts[0]}/{parts[1]}" if len(parts) > 1 else spec
                else:
                    pkg_name = spec.split("/")[0]
                imports.add(pkg_name)
    except (OSError, UnicodeDecodeError):
        pass
    return imports

def parse_python_manifests(target_dir: Path) -> Set[str]:
    declared = set()
    # 1. requirements.txt / requirements-dev.txt
    for req_file in target_dir.glob("requirements*.txt"):
        try:
            content = req_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Strip versions: pkg>=1.0, pkg==2.0, pkg[extra]
                m = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
                if m:
                    # Normalize python package names (hyphen to underscore)
                    pkg = m.group(1).lower().replace("-", "_")
                    declared.add(pkg)
        except (OSError, UnicodeDecodeError):
            pass

    # 2. pyproject.toml
    pyproject = target_dir / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="replace")
            # Basic regex extraction of dependencies list
            dep_matches = re.findall(r"""['"]([a-zA-Z0-9_\-\.]+)(?:[><=~^!].*)?['"]""", content)
            for d in dep_matches:
                declared.add(d.lower().replace("-", "_"))
        except (OSError, UnicodeDecodeError):
            pass

    return declared

def parse_node_manifest(target_dir: Path) -> Set[str]:
    declared = set()
    pkg_json = target_dir / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            for section in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
                if section in data and isinstance(data[section], dict):
                    declared.update(data[section].keys())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
    return declared

def scan_dependency_mismatches(target_dir: Path) -> Dict[str, Any]:
    target_dir = target_dir.resolve()
    py_stdlib = get_python_stdlib()

    # Discover local modules/folders in repository root to avoid flagging them
    local_python_modules = {p.stem for p in target_dir.glob("*.py")}
    local_python_modules.update({p.name for p in target_dir.iterdir() if p.is_dir() and (p / "__init__.py").exists()})
    local_python_modules.update({p.name for p in target_dir.iterdir() if p.is_dir()})

    py_imports_used: Dict[str, List[str]] = {}
    js_imports_used: Dict[str, List[str]] = {}

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            file_path = Path(root) / f
            ext = file_path.suffix.lower()
            rel_file = str(file_path.relative_to(target_dir)).replace("\\", "/")

            if ext == ".py":
                for imp in scan_python_imports(file_path):
                    py_imports_used.setdefault(imp, []).append(rel_file)
            elif ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]:
                for imp in scan_js_imports(file_path):
                    js_imports_used.setdefault(imp, []).append(rel_file)

    findings = []

    # Check Python dependencies
    has_python_files = bool(py_imports_used)
    if has_python_files:
        declared_py = parse_python_manifests(target_dir)
        has_py_manifest = bool(list(target_dir.glob("requirements*.txt"))) or (target_dir / "pyproject.toml").is_file()

        for imp, usage_files in py_imports_used.items():
            normalized_imp = imp.lower().replace("-", "_")
            if normalized_imp in py_stdlib or imp in local_python_modules or normalized_imp in local_python_modules:
                continue

            # Common mappings where import name differs from pypi name
            KNOWN_MAPPINGS = {
                "yaml": "pyyaml",
                "dotenv": "python_dotenv",
                "cv2": "opencv_python",
                "pil": "pillow",
                "bs4": "beautifulsoup4",
                "sklearn": "scikit_learn",
            }
            mapped = KNOWN_MAPPINGS.get(normalized_imp, normalized_imp)

            if declared_py and (normalized_imp not in declared_py and mapped not in declared_py):
                findings.append({
                    "ecosystem": "Python",
                    "package": imp,
                    "severity": "BLOCKER",
                    "type": "UNDECLARED_DEPENDENCY",
                    "description": f"Python module '{imp}' is imported in {len(usage_files)} file(s) but not declared in requirements.txt or pyproject.toml.",
                    "used_in": usage_files[:5]
                })

    # Check Node dependencies
    has_node_files = bool(js_imports_used)
    if has_node_files:
        declared_node = parse_node_manifest(target_dir)
        has_pkg_json = (target_dir / "package.json").is_file()

        for imp, usage_files in js_imports_used.items():
            if imp in NODE_BUILTINS or imp.startswith("node:"):
                continue

            if has_pkg_json and (imp not in declared_node):
                findings.append({
                    "ecosystem": "Node.js",
                    "package": imp,
                    "severity": "BLOCKER",
                    "type": "UNDECLARED_DEPENDENCY",
                    "description": f"npm package '{imp}' is imported in {len(usage_files)} file(s) but not listed in package.json.",
                    "used_in": usage_files[:5]
                })

    return {
        "findings_count": len(findings),
        "findings": findings
    }

def main():
    parser = argparse.ArgumentParser(description="Scan for undeclared and phantom dependencies")
    parser.add_argument("path", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    results = scan_dependency_mismatches(target)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n📦 Dependency Mismatch Scan: {target}")
        print(f"Total undeclared dependencies: {results['findings_count']}\n")
        for f in results["findings"]:
            print(f"[{f['severity']}] {f['ecosystem']} - {f['package']}")
            print(f"   {f['description']}")
            print(f"   Used in: {', '.join(f['used_in'])}\n")

if __name__ == "__main__":
    main()
