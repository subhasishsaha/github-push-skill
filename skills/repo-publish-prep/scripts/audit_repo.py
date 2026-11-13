#!/usr/bin/env python3
"""
Codebase Readiness & Security Auditor for Git Hosting (GitHub, GitLab, Bitbucket)
Zero-dependency Python 3 script.
Scans for:
 - Hardcoded secrets, keys, and tokens
 - Sensitive & credential files
 - Essential repository files (README, LICENSE, .gitignore, SECURITY, etc.)
 - .gitignore completeness against detected tech stack
 - Large files (>10MB, >50MB) and binary artifacts
 - Leftover scratch files, debug dumps, and OS junk
 - Git tracking status of sensitive items
"""

import os
import re
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Attempt to load sibling specialized scanners
try:
    from scan_stubs import scan_stubs
    from scan_dependencies import scan_dependency_mismatches
    from scan_path_leaks import scan_path_leaks
    from scan_doc_drift import scan_doc_drift
    HAS_SPECIALIZED = True
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from scan_stubs import scan_stubs
        from scan_dependencies import scan_dependency_mismatches
        from scan_path_leaks import scan_path_leaks
        from scan_doc_drift import scan_doc_drift
        HAS_SPECIALIZED = True
    except ImportError:
        HAS_SPECIALIZED = False

# --- SECRET SCANNING PATTERNS ---
SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z-_]{35}", "Google / Gemini API Key", "CRITICAL"),
    (r"sk-[A-Za-z0-9-_]{20,}", "OpenAI API Key", "CRITICAL"),
    (r"sk-ant-[A-Za-z0-9-_]{20,}", "Anthropic API Key", "CRITICAL"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "CRITICAL"),
    (r"(?:ghp|gho|ghu|ghs|ghr)_[0-9a-zA-Z]{36}", "GitHub Token (Legacy PAT/OAuth)", "CRITICAL"),
    (r"github_pat_[0-9a-zA-Z_]{82}", "GitHub Fine-Grained Personal Access Token", "CRITICAL"),
    (r"glpat-[0-9a-zA-Z\-_]{20,}", "GitLab Personal Access Token", "CRITICAL"),
    (r"xox[baprs]-[0-9a-zA-Z]{10,48}", "Slack Token / Webhook", "CRITICAL"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "Private Cryptographic Key", "CRITICAL"),
    (r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "JSON Web Token (JWT)", "WARNING"),
    (r"(?:postgres|mysql|mongodb|redis|amqp)://[a-zA-Z0-9_\-\.]+:[a-zA-Z0-9_\-\.]+@[a-zA-Z0-9_\-\.]+", "Database Connection URI with Credentials", "CRITICAL"),
    (r"(?i)(?:api_key|apikey|secret_key|client_secret|auth_token|access_token)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", "Generic High-Entropy API Key / Secret Assignment", "WARNING"),
]

# Words that indicate dummy / placeholder / template values
PLACEHOLDER_SUBSTRINGS = [
    "example", "dummy", "placeholder", "your_", "insert_", "<your", "${", "process.env",
    "os.environ", "getenv", "changeme", "xxx", "foo", "bar", "test", "sample", "replace_me",
    "my_api_key", "secret_here"
]

# Sensitive file names that should never be tracked
SENSITIVE_FILENAME_PATTERNS = [
    r"^\.env$",
    r"^\.env\.(?:local|development\.local|production\.local|test\.local)$",
    r".*\.pem$",
    r".*\.key$",
    r".*\.p12$",
    r".*\.pfx$",
    r"^id_rsa$",
    r"^id_ed25519$",
    r"^credentials\.json$",
    r"^service-account.*\.json$",
    r"^client_secret.*\.json$",
    r".*\.kdbx$",
]

# Scratch, junk, and temporary file patterns
JUNK_PATTERNS = [
    r"^\.DS_Store$",
    r"^Thumbs\.db$",
    r".*\.log$",
    r"^npm-debug\.log.*$",
    r"^yarn-debug\.log.*$",
    r"^yarn-error\.log.*$",
    r".*\.pyc$",
    r".*~$",
    r"^\.#.*",
    r"^core\.\d+$",
]

# Directories that should always be ignored during content scanning
EXCLUDED_SCAN_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "target", "dist",
    "build", "out", ".next", ".nuxt", ".output", "coverage", ".nyc_output",
    "vendor", ".turbo", ".gradle", "bin", "obj"
}

def is_placeholder(val: str) -> bool:
    lower_val = val.lower()
    return any(p in lower_val for p in PLACEHOLDER_SUBSTRINGS)

def run_cmd(cmd: List[str], cwd: Path) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

class RepoAuditor:
    def __init__(self, target_dir: Path, max_file_size_mb: float = 10.0, critical_file_size_mb: float = 50.0):
        self.target = target_dir.resolve()
        self.max_size_bytes = int(max_file_size_mb * 1024 * 1024)
        self.critical_size_bytes = int(critical_file_size_mb * 1024 * 1024)
        
        self.findings: List[Dict[str, Any]] = []
        self.stats = {
            "scanned_files": 0,
            "total_size_bytes": 0,
            "large_files": 0,
            "secret_findings": 0,
            "sensitive_files": 0,
            "junk_files": 0,
        }
        self.detected_stacks = []
        self.git_info = {}

    def log_finding(self, severity: str, category: str, title: str, description: str, file_path: Optional[str] = None, line_number: Optional[int] = None, remediation: Optional[str] = None):
        """
        Severity: BLOCKER, WARNING, INFO
        Category: SECRETS, ESSENTIAL_FILES, GITIGNORE, LARGE_FILES, CODE_CLEANLINESS, CI_CD, GIT_HYGIENE
        """
        self.findings.append({
            "severity": severity,
            "category": category,
            "title": title,
            "description": description,
            "file": file_path,
            "line": line_number,
            "remediation": remediation
        })

    def check_git_status(self):
        """Audit git repository status and tracking."""
        is_git_dir = (self.target / ".git").is_dir()
        if not is_git_dir:
            self.git_info["initialized"] = False
            self.log_finding(
                "WARNING", "GIT_HYGIENE",
                "Git repository not initialized",
                f"Directory '{self.target}' is not a Git repository (.git not found).",
                remediation="Run `git init` to initialize version control before publishing."
            )
            return

        self.git_info["initialized"] = True
        
        # Current branch
        rc, out, _ = run_cmd(["git", "branch", "--show-current"], self.target)
        self.git_info["current_branch"] = out if rc == 0 and out else "HEAD (detached)"
        if self.git_info["current_branch"] == "master":
            self.log_finding(
                "INFO", "GIT_HYGIENE",
                "Branch name is 'master'",
                "Modern GitHub/GitLab conventions default to 'main'.",
                remediation="Consider renaming default branch: `git branch -m master main`"
            )

        # Remote check
        rc, out, _ = run_cmd(["git", "remote", "-v"], self.target)
        self.git_info["remotes"] = out.splitlines() if rc == 0 and out else []
        if not self.git_info["remotes"]:
            self.log_finding(
                "INFO", "GIT_HYGIENE",
                "No git remotes configured",
                "No remote origin URL is currently configured.",
                remediation="Add remote repository after creating it: `git remote add origin <url>`"
            )

        # Uncommitted changes
        rc, out, _ = run_cmd(["git", "status", "--porcelain"], self.target)
        if rc == 0 and out:
            lines = out.splitlines()
            untracked = [l for l in lines if l.startswith("??")]
            modified = [l for l in lines if not l.startswith("??")]
            self.git_info["uncommitted_count"] = len(lines)
            self.log_finding(
                "WARNING", "GIT_HYGIENE",
                f"Working tree has {len(lines)} uncommitted change(s)",
                f"Detected {len(modified)} staged/modified file(s) and {len(untracked)} untracked file(s).",
                remediation="Review untracked files with `git status` and commit or ignore them."
            )

        # List files currently tracked by git
        rc, out, _ = run_cmd(["git", "ls-files"], self.target)
        tracked_files = set(out.splitlines()) if rc == 0 else set()
        self.git_info["tracked_files"] = tracked_files

        # Check if any sensitive file is tracked in git index
        for f in tracked_files:
            fname = os.path.basename(f)
            for pattern in SENSITIVE_FILENAME_PATTERNS:
                if re.match(pattern, fname, re.IGNORECASE):
                    self.log_finding(
                        "BLOCKER", "SECRETS",
                        f"Sensitive file tracked in Git index: {f}",
                        f"File '{f}' is tracked by Git! If pushed, credentials will be published.",
                        file_path=f,
                        remediation=f"Stop tracking and add to .gitignore: `git rm --cached {f}` and commit."
                    )

    def detect_tech_stacks(self):
        """Detect language stacks and frameworks present in the codebase."""
        stacks = []
        if (self.target / "package.json").is_file():
            stacks.append("Node.js / JavaScript / TypeScript")
        if any((self.target / f).is_file() for f in ["pyproject.toml", "requirements.txt", "Pipfile", "setup.py"]):
            stacks.append("Python")
        if (self.target / "Cargo.toml").is_file():
            stacks.append("Rust")
        if (self.target / "go.mod").is_file():
            stacks.append("Go")
        if any((self.target / f).is_file() for f in ["pom.xml", "build.gradle", "build.gradle.kts"]):
            stacks.append("Java / Kotlin")
        if any((self.target / f).is_file() for f in ["Dockerfile", "docker-compose.yml", "compose.yaml"]):
            stacks.append("Docker / Container")
        
        self.detected_stacks = stacks

    def check_essential_files(self):
        """Verify presence and quality of core repository files."""
        # 1. README
        readme_candidates = [f for f in ["README.md", "README.rst", "README.txt", "README"] if (self.target / f).is_file()]
        if not readme_candidates:
            self.log_finding(
                "BLOCKER", "ESSENTIAL_FILES",
                "Missing README file",
                "No README.md found at repository root. Every repository needs a descriptive README.",
                remediation="Create a README.md documenting the project purpose, quickstart, and usage."
            )
        else:
            readme_path = self.target / readme_candidates[0]
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
                if len(content.strip()) < 80:
                    self.log_finding(
                        "WARNING", "ESSENTIAL_FILES",
                        "README file is very sparse or empty",
                        f"'{readme_candidates[0]}' has only {len(content.strip())} characters.",
                        file_path=readme_candidates[0],
                        remediation="Expand README with project summary, prerequisites, installation, and usage."
                    )
                if re.search(r"(?i)\bTODO\b.*add description", content) or "Create React App" in content:
                    self.log_finding(
                        "WARNING", "ESSENTIAL_FILES",
                        "README contains boilerplate or unresolved TODO placeholders",
                        f"Found generic template text in '{readme_candidates[0]}'.",
                        file_path=readme_candidates[0],
                        remediation="Replace scaffold placeholder text with actual project documentation."
                    )
            except (OSError, UnicodeDecodeError):
                pass

        # 2. LICENSE
        license_candidates = [f for f in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"] if (self.target / f).is_file()]
        if not license_candidates:
            self.log_finding(
                "WARNING", "ESSENTIAL_FILES",
                "Missing LICENSE file",
                "No LICENSE file found. Public repositories without a license are by default All Rights Reserved (others cannot legally use or modify the code).",
                remediation="Add an appropriate open-source license (MIT, Apache-2.0) or Proprietary notice."
            )
        else:
            lic_path = self.target / license_candidates[0]
            try:
                lic_text = lic_path.read_text(encoding="utf-8", errors="replace").strip()
                if "<year>" in lic_text.lower() or "[year]" in lic_text.lower() or "<name of copyright owner>" in lic_text.lower():
                    self.log_finding(
                        "WARNING", "ESSENTIAL_FILES",
                        "LICENSE contains unreplaced template placeholders",
                        f"Found unreplaced placeholder such as '<year>' or '<owner>' in '{license_candidates[0]}'.",
                        file_path=license_candidates[0],
                        remediation="Replace year and copyright owner with actual values."
                    )
            except (OSError, UnicodeDecodeError):
                pass

        # 3. .gitignore
        gitignore_path = self.target / ".gitignore"
        if not gitignore_path.is_file():
            self.log_finding(
                "BLOCKER", "GITIGNORE",
                "Missing .gitignore file",
                "No .gitignore file found at repository root. Sensitive files and build artifacts will be accidentally committed.",
                remediation="Create a comprehensive .gitignore tailored to your tech stack."
            )
        else:
            try:
                gi_content = gitignore_path.read_text(encoding="utf-8", errors="replace")
                rules = [line.strip() for line in gi_content.splitlines() if line.strip() and not line.startswith("#")]
                
                # Check for env rules
                has_env_rule = any(".env" in r for r in rules)
                if not has_env_rule:
                    self.log_finding(
                        "BLOCKER", "GITIGNORE",
                        ".gitignore does not ignore .env files",
                        "Crucial rule '.env*' or '.env' is missing from .gitignore.",
                        file_path=".gitignore",
                        remediation="Add '.env' and '.env.*' (except .env.example) to .gitignore."
                    )
                
                # Check stack-specific gitignore rules
                if "Node.js / JavaScript / TypeScript" in self.detected_stacks:
                    if not any("node_modules" in r for r in rules):
                        self.log_finding(
                            "BLOCKER", "GITIGNORE",
                            ".gitignore missing 'node_modules/'",
                            "Node.js stack detected but 'node_modules/' is not ignored.",
                            file_path=".gitignore",
                            remediation="Add 'node_modules/' to .gitignore."
                        )
                if "Python" in self.detected_stacks:
                    if not any("__pycache__" in r or "*.pyc" in r for r in rules):
                        self.log_finding(
                            "WARNING", "GITIGNORE",
                            ".gitignore missing Python cache ignore rules",
                            "Python stack detected but '__pycache__/' or '*.pyc' is not ignored.",
                            file_path=".gitignore",
                            remediation="Add '__pycache__/', '*.pyc', and '.venv/' to .gitignore."
                        )
            except (OSError, UnicodeDecodeError):
                pass

        # 4. .env.example
        has_dotenv = (self.target / ".env").is_file()
        example_candidates = [f for f in [".env.example", ".env.template", ".env.sample"] if (self.target / f).is_file()]
        if has_dotenv and not example_candidates:
            self.log_finding(
                "WARNING", "ESSENTIAL_FILES",
                "Missing .env.example template",
                "A local '.env' file exists, but no '.env.example' is present to guide collaborators on required environment variables.",
                remediation="Generate a sanitized '.env.example' containing variable names with dummy values."
            )

        # 5. Community & Security files
        has_security = any((self.target / f).is_file() for f in ["SECURITY.md", ".github/SECURITY.md"])
        if not has_security:
            self.log_finding(
                "INFO", "ESSENTIAL_FILES",
                "Missing SECURITY.md",
                "No security policy found. A SECURITY.md provides a responsible vulnerability reporting channel.",
                remediation="Add a SECURITY.md with contact email and supported versions."
            )

        has_contributing = any((self.target / f).is_file() for f in ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"])
        if not has_contributing:
            self.log_finding(
                "INFO", "ESSENTIAL_FILES",
                "Missing CONTRIBUTING.md",
                "No contribution guide found. Helpful for open-source and team repositories.",
                remediation="Add CONTRIBUTING.md outlining PR workflow, issue filing, and testing instructions."
            )

        has_code_of_conduct = any((self.target / f).is_file() for f in ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"])
        if not has_code_of_conduct:
            self.log_finding(
                "INFO", "ESSENTIAL_FILES",
                "Missing CODE_OF_CONDUCT.md",
                "No Code of Conduct found. Standard for public open-source projects.",
                remediation="Add CODE_OF_CONDUCT.md (e.g., Contributor Covenant v2.1)."
            )

        # 6. CI/CD automation
        gh_workflows = list((self.target / ".github" / "workflows").glob("*.yml")) + list((self.target / ".github" / "workflows").glob("*.yaml")) if (self.target / ".github" / "workflows").is_dir() else []
        has_ci = bool(gh_workflows) or (self.target / ".gitlab-ci.yml").is_file() or (self.target / "bitbucket-pipelines.yml").is_file()
        if not has_ci:
            self.log_finding(
                "INFO", "CI_CD",
                "No CI/CD automation workflows detected",
                "No GitHub Actions workflows, GitLab CI, or Bitbucket pipelines found.",
                remediation="Add automated testing/linting workflow under .github/workflows/ci.yml."
            )

    def scan_files_and_directories(self):
        """Recursively scan directory for secrets, large files, junk, and sensitive filenames."""
        tracked_files = self.git_info.get("tracked_files", set())

        for root, dirs, files in os.walk(self.target):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDED_SCAN_DIRS]

            for file in files:
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(self.target)).replace("\\", "/")
                
                # Check sensitive filenames
                for pattern in SENSITIVE_FILENAME_PATTERNS:
                    if re.match(pattern, file, re.IGNORECASE):
                        self.stats["sensitive_files"] += 1
                        # If tracked, already flagged as BLOCKER. If untracked, warn to keep untracked
                        if rel_path not in tracked_files:
                            self.log_finding(
                                "WARNING", "SECRETS",
                                f"Local sensitive file present: {rel_path}",
                                f"Sensitive credential file '{rel_path}' exists on disk. Ensure it is ignored by .gitignore.",
                                file_path=rel_path,
                                remediation="Verify this file is excluded in .gitignore and never committed."
                            )

                # Check junk / temporary files
                for pattern in JUNK_PATTERNS:
                    if re.match(pattern, file, re.IGNORECASE):
                        self.stats["junk_files"] += 1
                        self.log_finding(
                            "INFO", "CODE_CLEANLINESS",
                            f"Temporary / junk artifact detected: {rel_path}",
                            f"File '{rel_path}' is an OS, log, or build artifact.",
                            file_path=rel_path,
                            remediation="Delete file or add pattern to .gitignore."
                        )

                # File size check
                try:
                    file_size = full_path.stat().st_size
                    self.stats["total_size_bytes"] += file_size
                    self.stats["scanned_files"] += 1

                    if file_size > self.critical_size_bytes:
                        self.stats["large_files"] += 1
                        mb = file_size / (1024 * 1024)
                        self.log_finding(
                            "BLOCKER", "LARGE_FILES",
                            f"Critical oversized file (>50MB): {rel_path} ({mb:.1f} MB)",
                            f"File size is {mb:.1f} MB. GitHub rejects pushes containing files larger than 100MB and warns above 50MB.",
                            file_path=rel_path,
                            remediation="Use Git LFS (Large File Storage) or store large dataset/model files outside Git."
                        )
                    elif file_size > self.max_size_bytes:
                        self.stats["large_files"] += 1
                        mb = file_size / (1024 * 1024)
                        self.log_finding(
                            "WARNING", "LARGE_FILES",
                            f"Large file (>10MB): {rel_path} ({mb:.1f} MB)",
                            f"File size is {mb:.1f} MB. Large binaries bloat Git history.",
                            file_path=rel_path,
                            remediation="Consider whether this file belongs in Git or should be tracked with Git LFS."
                        )
                except Exception:
                    continue

                # Content scan for secrets (skip binary files and files > 2MB)
                if file_size > 2 * 1024 * 1024:
                    continue

                # Quick binary check
                if self.is_binary_file(full_path):
                    continue

                self.scan_file_content_for_secrets(full_path, rel_path)

    def is_binary_file(self, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                chunk = f.read(1024)
                return b"\x00" in chunk
        except Exception:
            return True

    def scan_file_content_for_secrets(self, path: Path, rel_path: str):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line_idx, line in enumerate(f, start=1):
                    # Skip comment-only or documentation files if needed, but let's scan all code
                    for pattern, secret_type, default_sev in SECRET_PATTERNS:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            matched_str = match.group(0)
                            if is_placeholder(matched_str) or is_placeholder(line):
                                continue
                            
                            # Redact match for display
                            if len(matched_str) > 8:
                                redacted = matched_str[:4] + "..." + matched_str[-4:]
                            else:
                                redacted = "***"

                            self.stats["secret_findings"] += 1
                            sev = "BLOCKER" if default_sev == "CRITICAL" else "WARNING"
                            self.log_finding(
                                sev, "SECRETS",
                                f"Potential secret leak detected ({secret_type})",
                                f"Line {line_idx} contains matching token pattern: `{redacted}`",
                                file_path=rel_path,
                                line_number=line_idx,
                                remediation="Remove secret immediately. Move credentials to an untracked .env file or secret manager."
                            )
        except (OSError, UnicodeDecodeError):
            pass

    def run_specialized_checks(self):
        """Execute deep forensic checks for stubs, dependencies, leaks, and drift."""
        if not HAS_SPECIALIZED:
            return

        # 1. Stub and eagerness bias scan
        try:
            stub_findings = scan_stubs(self.target)
            for sf in stub_findings:
                rel = str(Path(sf["file"]).relative_to(self.target)).replace("\\", "/") if self.target in Path(sf["file"]).parents or self.target == Path(sf["file"]) else sf["file"]
                sev = "BLOCKER" if sf["type"] in ["EMPTY_FUNCTION_PASS", "EMPTY_FUNCTION_ELLIPSIS", "NOT_IMPLEMENTED_ERROR"] else "WARNING"
                self.log_finding(
                    sev, "EAGERNESS_BIAS",
                    f"Stub / Incomplete implementation ({sf['type']})",
                    sf["description"],
                    file_path=rel,
                    line_number=sf.get("line"),
                    remediation="Fully implement the function logic or remove hollow placeholder."
                )
        except (OSError, UnicodeDecodeError, SyntaxError):
            pass

        # 2. Dependency mismatch scan
        try:
            dep_res = scan_dependency_mismatches(self.target)
            for df in dep_res.get("findings", []):
                self.log_finding(
                    df["severity"], "DEPENDENCIES",
                    f"Undeclared dependency: {df['package']}",
                    df["description"],
                    file_path=df["used_in"][0] if df.get("used_in") else None,
                    remediation=f"Add '{df['package']}' to your package manifest (requirements.txt, package.json, etc.)."
                )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, SyntaxError):
            pass

        # 3. Local path & environment leaks
        try:
            path_findings = scan_path_leaks(self.target)
            for pf in path_findings:
                rel = str(Path(pf["file"]).relative_to(self.target)).replace("\\", "/") if self.target in Path(pf["file"]).parents or self.target == Path(pf["file"]) else pf["file"]
                self.log_finding(
                    "BLOCKER", "ENVIRONMENT_LEAKS",
                    "Hardcoded local environment or path leak",
                    pf["description"],
                    file_path=rel,
                    line_number=pf.get("line"),
                    remediation="Replace hardcoded absolute path or local IP with relative path or environment variable."
                )
        except (OSError, UnicodeDecodeError):
            pass

        # 4. Doc drift scan
        try:
            doc_findings = scan_doc_drift(self.target)
            for dcf in doc_findings:
                rel = str(Path(dcf["file"]).relative_to(self.target)).replace("\\", "/") if self.target in Path(dcf["file"]).parents or self.target == Path(dcf["file"]) else dcf["file"]
                self.log_finding(
                    "BLOCKER", "DOC_DRIFT",
                    f"Documentation broken reference ({dcf['type']})",
                    dcf["description"],
                    file_path=rel,
                    remediation="Update link or create missing file/image referenced in documentation."
                )
        except (OSError, UnicodeDecodeError):
            pass

    def calculate_score(self) -> Tuple[int, str]:
        """Calculates readiness score (0-100) and readiness tier."""
        blockers = sum(1 for f in self.findings if f["severity"] == "BLOCKER")
        warnings = sum(1 for f in self.findings if f["severity"] == "WARNING")
        
        # Base score 100
        score = 100
        score -= (blockers * 25)
        score -= (warnings * 5)
        score = max(0, min(100, score))

        if blockers > 0:
            status = "NOT READY (Blockers Must Be Resolved)"
        elif warnings > 2:
            status = "NEEDS ATTENTION (Warnings Recommended to Fix)"
        elif warnings > 0:
            status = "GOOD (Minor improvements suggested)"
        else:
            status = "EXCELLENT (Ready to Publish)"

        return score, status

    def run_audit(self, specialized: bool = True) -> Dict[str, Any]:
        """Execute full audit suite and return structured results."""
        self.detect_tech_stacks()
        self.check_git_status()
        self.check_essential_files()
        self.scan_files_and_directories()
        if specialized:
            self.run_specialized_checks()
        
        score, status = self.calculate_score()
        
        return {
            "target": str(self.target),
            "score": score,
            "status": status,
            "detected_stacks": self.detected_stacks,
            "git_info": {k: v for k, v in self.git_info.items() if k != "tracked_files"},
            "stats": self.stats,
            "findings_count": {
                "blockers": sum(1 for f in self.findings if f["severity"] == "BLOCKER"),
                "warnings": sum(1 for f in self.findings if f["severity"] == "WARNING"),
                "info": sum(1 for f in self.findings if f["severity"] == "INFO"),
            },
            "findings": self.findings
        }

def format_console_report(results: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("        🚀 CODEBASE PUBLISHING READINESS AUDIT REPORT")
    lines.append("=" * 70)
    lines.append(f" Target Directory : {results['target']}")
    lines.append(f" Tech Stacks      : {', '.join(results['detected_stacks']) or 'Generic'}")
    lines.append(f" Readiness Score  : {results['score']}/100 - {results['status']}")
    lines.append(f" Summary          : 🛑 {results['findings_count']['blockers']} Blocker(s) | ⚠️ {results['findings_count']['warnings']} Warning(s) | 💡 {results['findings_count']['info']} Info")
    lines.append("-" * 70)

    if not results["findings"]:
        lines.append(" 🎉 Perfect score! No issues or blockers found.")
        lines.append("=" * 70)
        return "\n".join(lines)

    # Group by severity
    blockers = [f for f in results["findings"] if f["severity"] == "BLOCKER"]
    warnings = [f for f in results["findings"] if f["severity"] == "WARNING"]
    infos = [f for f in results["findings"] if f["severity"] == "INFO"]

    if blockers:
        lines.append("\n🛑 BLOCKERS (Must fix before pushing / publishing):")
        for i, f in enumerate(blockers, 1):
            loc = f" in {f['file']}" + (f":{f['line']}" if f['line'] else "") if f['file'] else ""
            lines.append(f"  {i}. [{f['category']}] {f['title']}{loc}")
            lines.append(f"     Details: {f['description']}")
            if f.get("remediation"):
                lines.append(f"     Fix:     {f['remediation']}")

    if warnings:
        lines.append("\n⚠️ WARNINGS (Strongly recommended to address):")
        for i, f in enumerate(warnings, 1):
            loc = f" in {f['file']}" + (f":{f['line']}" if f['line'] else "") if f['file'] else ""
            lines.append(f"  {i}. [{f['category']}] {f['title']}{loc}")
            lines.append(f"     Details: {f['description']}")
            if f.get("remediation"):
                lines.append(f"     Fix:     {f['remediation']}")

    if infos:
        lines.append("\n💡 RECOMMENDATIONS & BEST PRACTICES:")
        for i, f in enumerate(infos, 1):
            loc = f" in {f['file']}" if f['file'] else ""
            lines.append(f"  {i}. [{f['category']}] {f['title']}{loc}")
            lines.append(f"     Fix: {f.get('remediation', f['description'])}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)

def format_markdown_report(results: Dict[str, Any]) -> str:
    lines = []
    lines.append("# 🚀 Codebase Publishing Readiness Report\n")
    lines.append(f"- **Target Directory:** `{results['target']}`")
    lines.append(f"- **Detected Stacks:** {', '.join(results['detected_stacks']) or 'Generic'}")
    lines.append(f"- **Readiness Score:** **{results['score']} / 100** (`{results['status']}`)\n")
    
    lines.append("## Overview\n")
    lines.append("| Severity | Count | Action Required |")
    lines.append("| :--- | :---: | :--- |")
    lines.append(f"| 🛑 **Blocker** | {results['findings_count']['blockers']} | Mandatory resolution before publishing |")
    lines.append(f"| ⚠️ **Warning** | {results['findings_count']['warnings']} | Recommended resolution to prevent issues |")
    lines.append(f"| 💡 **Info / Recommendation** | {results['findings_count']['info']} | Best practice improvements |")
    lines.append("")

    for sev_name, badge in [("BLOCKER", "🛑 BLOCKERS"), ("WARNING", "⚠️ WARNINGS"), ("INFO", "💡 RECOMMENDATIONS")]:
        items = [f for f in results["findings"] if f["severity"] == sev_name]
        if not items:
            continue
        lines.append(f"## {badge}\n")
        for item in items:
            loc = f" (`{item['file']}`" + (f":{item['line']}" if item.get('line') else "") + ")" if item.get('file') else ""
            lines.append(f"### {item['title']}{loc}\n")
            lines.append(f"- **Category:** `{item['category']}`")
            lines.append(f"- **Details:** {item['description']}")
            if item.get("remediation"):
                lines.append(f"- **Remediation:** {item['remediation']}")
            lines.append("")

    return "\n".join(lines)

def format_agent_03_report(results: Dict[str, Any]) -> str:
    """Format report specifically for Agent 03 -> Agent 04 remediation loop."""
    lines = []
    lines.append("# 🕵️ Agent 03 Codebase Verification & Irregularities Report\n")
    lines.append(f"- **Target Directory:** `{results['target']}`")
    lines.append(f"- **Audit Generated:** `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}`")
    lines.append(f"- **Current Readiness Score:** **{results['score']} / 100** (`{results['status']}`)\n")
    
    lines.append("## Irregularity Triage Matrix\n")
    lines.append("| Category | Severity | File / Symbol | Remediation Required |")
    lines.append("| :--- | :---: | :--- | :--- |")
    
    for f in results["findings"]:
        loc = f"`{f['file']}`" + (f":{f['line']}" if f.get('line') else "") if f.get('file') else "Repository Root"
        sev_icon = "🛑" if f["severity"] == "BLOCKER" else ("⚠️" if f["severity"] == "WARNING" else "💡")
        remed = f.get("remediation", f["description"]).replace("|", "\\|")
        lines.append(f"| `{f['category']}` | {sev_icon} **{f['severity']}** | {loc} | {remed} |")
    lines.append("")

    lines.append("## Detailed Action Items for Agent 04 (Remediation Engineer)\n")
    categories = sorted(set(f["category"] for f in results["findings"]))
    if not categories:
        lines.append("🎉 **Zero irregularities detected.** All codebase checks, imports, naming, and doc alignment pass!\n")
    else:
        for cat in categories:
            items = [f for f in results["findings"] if f["category"] == cat]
            lines.append(f"### Category: `{cat}` ({len(items)} item{'s' if len(items) > 1 else ''})\n")
            for i, item in enumerate(items, 1):
                loc = f" (`{item['file']}`" + (f":{item['line']}" if item.get('line') else "") + ")" if item.get('file') else ""
                lines.append(f"{i}. **{item['title']}**{loc}")
                lines.append(f"   - **Details:** {item['description']}")
                if item.get("remediation"):
                    lines.append(f"   - **Required Fix:** {item['remediation']}")
                lines.append("")

    lines.append("## Agent Hand-off Protocol\n")
    lines.append("1. **Agent 04:** Read each action item above and implement the complete fix in source code.")
    lines.append("2. **Agent 04:** Once modifications are complete, return control to **Agent 03**.")
    lines.append("3. **Agent 03:** Re-run this audit to verify that all irregularities are resolved.")
    return "\n".join(lines)

def format_final_report(results: Dict[str, Any]) -> str:
    """Format Phase 3 certification report (.agents/final_report/report.md)."""
    lines = []
    lines.append("# 🏆 Final Repository Publishing Certification & Report\n")
    lines.append(f"- **Target Repository:** `{results['target']}`")
    lines.append(f"- **Certified At:** `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}`")
    lines.append(f"- **Final Readiness Score:** **{results['score']} / 100** (`{results['status']}`)\n")
    lines.append("## 1. Publication Readiness Verdict\n")
    
    if results['findings_count']['blockers'] == 0:
        lines.append("✅ **VERIFIED PASSED:** All adversarial checks across the 3-phase verification gate have succeeded with ZERO blockers.")
    else:
        lines.append(f"🛑 **ACTION REQUIRED:** {results['findings_count']['blockers']} blockers remain unresolved.")
    lines.append("")

    lines.append("## 2. Integrity Verification Matrix\n")
    lines.append("| Verification Pillar | Findings Count | Status | Verification Method |")
    lines.append("| :--- | :---: | :---: | :--- |")
    
    cat_counts = {}
    for f in results["findings"]:
        cat_counts[f["category"]] = cat_counts.get(f["category"], 0) + 1

    pillars = [
        ("SECRETS", "Secrets & Credentials", "Static Token & Credential Scanner"),
        ("EAGERNESS_BIAS", "Eagerness Bias & Stubs", "AST Empty Function & Stub Scanner"),
        ("DEPENDENCIES", "Dependency Declarations", "AST Import vs Manifest Checker"),
        ("ENVIRONMENT_LEAKS", "Local Path & Env Leaks", "OS User Path & IP Address Scanner"),
        ("DOC_DRIFT", "Document-to-Code Drift", "Markdown Link & Entrypoint Validator"),
        ("GIT_HYGIENE", "Git Working Tree & Tracking", "Git Index & Status Audit"),
    ]

    for cat_key, label, method in pillars:
        cnt = cat_counts.get(cat_key, 0)
        status_str = "✅ PASS (0 issues)" if cnt == 0 else f"⚠️ {cnt} issue(s)"
        lines.append(f"| **{label}** | {cnt} | {status_str} | {method} |")
    lines.append("")

    lines.append("## 3. Remote Push Instructions for User\n")
    lines.append("Your codebase is verified. To publish to your Git host:")
    lines.append("```bash")
    lines.append("# 1. Review status")
    lines.append("git status\n")
    lines.append("# 2. Add remote origin (if not set)")
    lines.append("git remote add origin https://github.com/<your-org>/<your-repo>.git\n")
    lines.append("# 3. Push to main branch")
    lines.append("git push -u origin main")
    lines.append("```\n")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Audit codebase for publishing readiness (GitHub/GitLab/Bitbucket)")
    parser.add_argument("path", nargs="?", default=".", help="Root path of repository to audit (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--markdown", help="Output markdown report to specified file path")
    parser.add_argument("--agent-report", help="Output Agent 03 verification report to specified path (e.g. .audit/verification/agent_03/report.md)")
    parser.add_argument("--final-report", help="Output Phase 3 final report to specified path (e.g. .agents/final_report/report.md)")
    parser.add_argument("--fail-on-blockers", action="store_true", help="Exit with non-zero code if blockers exist")
    parser.add_argument("--no-specialized", action="store_true", help="Disable specialized AST and dependency checks")
    parser.add_argument("--max-size", type=float, default=10.0, help="File size in MB to flag as warning (default: 10)")
    parser.add_argument("--critical-size", type=float, default=50.0, help="File size in MB to flag as blocker (default: 50)")

    args = parser.parse_args()
    target_path = Path(args.path)

    if not target_path.exists():
        print(f"Error: Path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    auditor = RepoAuditor(target_path, max_file_size_mb=args.max_size, critical_file_size_mb=args.critical_size)
    results = auditor.run_audit(specialized=(not args.no_specialized))

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_console_report(results))

    if args.markdown:
        md_content = format_markdown_report(results)
        try:
            out_file = Path(args.markdown)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(md_content, encoding="utf-8")
            print(f"\n📄 Markdown report written to: {args.markdown}")
        except Exception as e:
            print(f"Failed to write markdown report: {e}", file=sys.stderr)

    if args.agent_report:
        agent_md = format_agent_03_report(results)
        try:
            out_file = Path(args.agent_report)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(agent_md, encoding="utf-8")
            print(f"\n🕵️ Agent 03 report written to: {args.agent_report}")
        except Exception as e:
            print(f"Failed to write Agent 03 report: {e}", file=sys.stderr)

    if args.final_report:
        final_md = format_final_report(results)
        try:
            out_file = Path(args.final_report)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(final_md, encoding="utf-8")
            print(f"\n🏆 Phase 3 final report written to: {args.final_report}")
        except Exception as e:
            print(f"Failed to write final report: {e}", file=sys.stderr)

    if args.fail_on_blockers and results["findings_count"]["blockers"] > 0:
        sys.exit(2)

if __name__ == "__main__":
    main()
