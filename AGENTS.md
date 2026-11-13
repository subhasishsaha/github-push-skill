# Agent Instructions: Codebase Publishing & Hosting Preparation

This repository contains the **`repo-publish-prep`** skill — a universal, harness-agnostic toolkit for preparing, auditing, sanitizing, and packaging codebases for GitHub, GitLab, Bitbucket, and remote Git hosting.

## How to Execute This Skill

When the user asks to prepare, review, audit, or clean up a codebase for GitHub or Git publishing:

1. **Activate the Main Skill Runbook:**
   Read and follow [skills/repo-publish-prep/SKILL.md](./skills/repo-publish-prep/SKILL.md).

2. **Run the Pre-Flight Auditor:**
   Execute the standalone auditor via your shell/terminal tool:
   ```bash
   python skills/repo-publish-prep/scripts/audit_repo.py <TARGET_DIRECTORY>
   ```

3. **Check for Environment Variables:**
   If environment variables or `.env` files are used, run:
   ```bash
   python skills/repo-publish-prep/scripts/generate_env_example.py <TARGET_DIRECTORY>
   ```

4. **Remediate Findings:**
   Refer to the templates in [skills/repo-publish-prep/templates/](./skills/repo-publish-prep/templates/) for stack-appropriate `.gitignore`, documentation, and CI/CD workflows.

5. **Verify Clean Bill of Health:**
   Ensure zero blockers before advising the user to commit and push.
