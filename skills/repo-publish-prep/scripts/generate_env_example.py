#!/usr/bin/env python3
"""
Environment Variable Template Generator (.env.example)
Scans existing .env files and source code for environment variable references,
stripping sensitive values and outputting a clean, sanitized .env.example.
Zero-dependency Python 3 script.
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, Set

# Patterns to locate environment variable usages in code
CODE_ENV_PATTERNS = [
    r"process\.env\.([A-Z0-9_]+)",                   # Node.js
    r"os\.environ(?:\[['\"]|\.get\(['\"])([A-Z0-9_]+)", # Python
    r"os\.getenv\(['\"]([A-Z0-9_]+)",               # Python
    r"env::var\(['\"]([A-Z0-9_]+)",                  # Rust
    r"os\.Getenv\(['\"]([A-Z0-9_]+)",               # Go
    r"System\.getenv\(['\"]([A-Z0-9_]+)",           # Java
    r"\$\{([A-Z0-9_]+)\}",                           # Shell / Docker compose
]

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "target", "dist", "build", ".next", ".nuxt", "coverage"
}

def guess_placeholder(var_name: str, original_val: str = "") -> str:
    lower = var_name.lower()
    if any(k in lower for k in ["port"]):
        return "3000" if not original_val else original_val
    if any(k in lower for k in ["host"]):
        return "localhost"
    if any(k in lower for k in ["url", "uri", "endpoint"]):
        if "db" in lower or "database" in lower or "postgres" in lower or "mongo" in lower:
            return "postgresql://postgres:password@localhost:5432/myapp_dev"
        return "https://api.example.com"
    if any(k in lower for k in ["key", "secret", "token", "password", "auth"]):
        return f"your_{lower}_here"
    if any(k in lower for k in ["id", "client_id"]):
        return f"your_{lower}_here"
    if any(k in lower for k in ["debug", "verbose"]):
        return "true"
    if any(k in lower for k in ["env", "environment", "node_env"]):
        return "development"
    return "your_value_here"

def parse_existing_env(file_path: Path) -> Dict[str, str]:
    vars_found = {}
    if not file_path.is_file():
        return vars_found

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                vars_found[key] = val
    except Exception as e:
        print(f"Warning: could not read {file_path}: {e}", file=sys.stderr)
    return vars_found

def scan_codebase_for_env_vars(target_dir: Path) -> Set[str]:
    discovered = set()
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            # Only scan source files
            ext = os.path.splitext(file)[1].lower()
            if ext not in [".js", ".ts", ".jsx", ".tsx", ".py", ".go", ".rs", ".java", ".sh", ".yaml", ".yml", ".json"]:
                continue
            
            file_path = Path(root) / file
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for pattern in CODE_ENV_PATTERNS:
                    for match in re.finditer(pattern, content):
                        var_name = match.group(1)
                        if len(var_name) > 1 and not var_name.startswith("_"):
                            discovered.add(var_name)
            except (OSError, UnicodeDecodeError):
                pass
    return discovered

def generate_env_example(target_dir: Path, output_file: Path, overwrite: bool = False):
    existing_env_files = [target_dir / f for f in [".env", ".env.local", ".env.development"] if (target_dir / f).is_file()]
    
    parsed_vars = {}
    for env_file in existing_env_files:
        parsed_vars.update(parse_existing_env(env_file))

    code_vars = scan_codebase_for_env_vars(target_dir)

    all_keys = sorted(set(list(parsed_vars.keys()) + list(code_vars)))

    if not all_keys:
        print("No environment variables found in .env files or source code.")
        return

    if output_file.exists() and not overwrite:
        print(f"File '{output_file}' already exists. Use --force to overwrite.", file=sys.stderr)
        return

    lines = [
        "# =============================================================================",
        "# ENVIRONMENT VARIABLES TEMPLATE (.env.example)",
        "# Copy this file to .env and configure values for your local environment.",
        "# DO NOT commit your real .env file with sensitive credentials to Git!",
        "# =============================================================================\n"
    ]

    for key in all_keys:
        orig = parsed_vars.get(key, "")
        placeholder = guess_placeholder(key, orig)
        lines.append(f"{key}={placeholder}")

    lines.append("")
    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Generated sanitized template with {len(all_keys)} variables at: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate sanitized .env.example from code and existing .env files")
    parser.add_argument("path", nargs="?", default=".", help="Root directory of repository (default: current directory)")
    parser.add_argument("-o", "--output", default=".env.example", help="Output file name (default: .env.example)")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing output file")

    args = parser.parse_args()
    target = Path(args.path).resolve()
    out = target / args.output

    generate_env_example(target, out, overwrite=args.force)

if __name__ == "__main__":
    main()
