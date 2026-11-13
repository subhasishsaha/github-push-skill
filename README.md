# 🚀 repo-publish-prep

[![CI Status](https://github.com/antigravity-community/repo-publish-prep/actions/workflows/ci.yml/badge.svg)](https://github.com/antigravity-community/repo-publish-prep/actions)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-brightgreen.svg)](https://python.org)

**`repo-publish-prep`** is an autonomous Agent skill and developer toolkit designed to audit, sanitize, package, and standardize codebases before pushing or publishing to **GitHub, GitLab, Bitbucket**, or other remote Git hosting platforms.

---

## 🎯 Why This Skill Exists

When developers or AI coding agents build software, repositories often end up with:
- Accidental `.env` files or hardcoded API keys.
- Missing or generic `.gitignore` leaving bloated `node_modules/`, `__pycache__/`, or OS junk (`.DS_Store`).
- Absent or boilerplate `README.md` files without installation or configuration details.
- Missing `LICENSE` files (which legally makes code proprietary by default).
- Oversized binaries or dataset files (> 50MB) that trigger Git push rejections.
- No CI/CD workflows, issue templates, or security reporting mechanisms.

This skill automates the **entire pre-flight verification gate**, giving agents and teams a clean, publication-ready repository with one command.

---

## 🏛️ The 7-Pillar Readiness Framework

```mermaid
flowchart LR
    A["1. Secrets Audit\n& Zero-Leak"] --> B["2. Git Hygiene\n& .gitignore"]
    B --> C["3. Documentation\n& Presentation"]
    C --> D["4. Legal &\nLicensing"]
    D --> E["5. Code Cleanup\n& EditorConfig"]
    E --> F["6. CI/CD & Issue\nTemplates"]
    F --> G["7. Verification\n& Commit Staging"]
```

1. **Secret & Credential Sanitization:** Zero-dependency AST/regex secret scanner (Google, OpenAI, AWS, GitHub PATs, JWTs, DB credentials, private keys).
2. **Git Hygiene & .gitignore Completeness:** Validates `.gitignore` against detected tech stacks (Node, Python, Go, Rust, Docker) and audits git index tracking.
3. **Repository Documentation:** High-impact, modular `README.md`, `CONTRIBUTING.md`, and `SECURITY.md`.
4. **Licensing & Legal Compliance:** Guidance and verification for MIT, Apache-2.0, BSD-3-Clause, or Proprietary licenses.
5. **Code Quality & Cleanliness:** Purges scratch files, debug logs, and establishes universal `.editorconfig`.
6. **CI/CD & Automation:** Multi-platform CI workflows (GitHub Actions, GitLab CI, Bitbucket Pipelines), issue forms, and Dependabot.
7. **Pre-Flight Verification:** Automated readiness scoring (0–100) with diagnostic report output.

---

## 📂 Repository Structure

```text
├── plugin.json                                # Plugin manifest for Antigravity & Agent ecosystems
├── README.md                                  # Repository overview and documentation
├── LICENSE                                    # Apache-2.0 license
├── .gitignore                                 # Clean gitignore configuration
├── .editorconfig                              # Standardized editor config
├── .github/
│   ├── workflows/ci.yml                       # CI test & audit pipeline
│   └── dependabot.yml                         # Automated dependency alerts
│
├── skills/
│   └── repo-publish-prep/
│       ├── SKILL.md                           # Main agent runbook & instructions
│       │
│       ├── scripts/                           # Zero-dependency Python 3 CLI utilities
│       │   ├── audit_repo.py                  # Codebase readiness auditor & scorecard
│       │   └── generate_env_example.py        # Automated .env.example generator
│       │
│       ├── templates/                         # Battle-tested templates
│       │   ├── gitignore/                     # Node, Python, Go, Rust, Universal
│       │   ├── docs/                          # README, CONTRIBUTING, SECURITY, EditorConfig
│       │   ├── github/                        # Workflows, Issue & PR templates, Dependabot
│       │   ├── gitlab/                        # .gitlab-ci.yml
│       │   └── bitbucket/                     # bitbucket-pipelines.yml
│       │
│       └── references/                        # Deep runbooks & guides
│           ├── readiness_checklist.md         # 50-point pre-flight checklist
│           ├── secrets_remediation.md         # Git history scrubbing (git-filter-repo)
│           ├── license_selection_guide.md     # SPDX license decision tree
│           └── platform_feature_matrix.md     # Multi-platform feature mapping
│
└── tests/
    └── test_audit_repo.py                     # Unit test suite
```

---

## 💻 CLI Usage (Standalone)

The bundled scripts require **Python 3.10+** and have **zero external dependencies**.

### 1. Run the Codebase Auditor

```bash
# Scan current directory and print console report
python skills/repo-publish-prep/scripts/audit_repo.py .

# Output machine-readable JSON for automated tooling
python skills/repo-publish-prep/scripts/audit_repo.py . --json

# Generate a Markdown report artifact
python skills/repo-publish-prep/scripts/audit_repo.py . --markdown READINESS_REPORT.md

# Fail with non-zero exit code if blockers are detected (ideal for CI)
python skills/repo-publish-prep/scripts/audit_repo.py . --fail-on-blockers
```

### 2. Generate `.env.example`

Scans existing `.env` files and source code for environment variables, strips real values, and outputs safe placeholders:

```bash
python skills/repo-publish-prep/scripts/generate_env_example.py .
```

---

## 🤖 Using as an Agent Skill

In Antigravity or compatible AI coding assistants:

1. **Install or Mount:**
   Add to `.agents/skills/` or install as a plugin via `plugin.json`.
2. **Activate:**
   Tell the agent:
   > *"Prepare this codebase for publishing on GitHub."*  
   > or  
   > *"Run a final review audit before I push this repo."*
3. The agent activates `repo-publish-prep`, scans for blockers, prompts you for any missing preferences (e.g. license or repository name), scaffolds required workflows, and stages clean commits.

---

## 🧪 Testing

Run the unit test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).
