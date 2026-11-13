# Codebase Readiness Checklist (Pre-Flight Gate)

Use this checklist as a comprehensive verification gate before pushing or publishing a repository to GitHub, GitLab, Bitbucket, or any public/private code hosting platform.

---

## 1. Secrets & Credentials (Zero-Leak Gate)
- [ ] No hardcoded API keys, tokens, or private keys in source code or commit messages.
- [ ] No `.env` files tracked or committed.
- [ ] `.env.example` or `.env.template` exists with sanitized dummy values.
- [ ] `.gitignore` contains rules for `.env`, `*.pem`, `*.key`, `id_rsa`, `credentials.json`.
- [ ] Git tracking verified (`git ls-files` contains zero credential files).

## 2. Documentation & Presentation
- [ ] `README.md` exists with clear project title and description.
- [ ] Prerequisites and installation steps documented and verified on a fresh environment.
- [ ] Usage examples and code snippets provided.
- [ ] Configuration parameters / environment variable table documented.
- [ ] License badge / link present in README.
- [ ] `CONTRIBUTING.md` provides PR, issue filing, and testing instructions.
- [ ] `SECURITY.md` defines vulnerability disclosure policy and private reporting channel.
- [ ] `CODE_OF_CONDUCT.md` present (recommended for public open-source repos).

## 3. Legal & Licensing
- [ ] `LICENSE` file exists at repository root.
- [ ] License type matches package manifest (`package.json`, `pyproject.toml`, etc.).
- [ ] Copyright year and owner placeholders replaced with actual values.
- [ ] Third-party licenses respected and attributed if bundling external code.

## 4. Code Quality & Cleanliness
- [ ] Temporary files, debug scripts, test dumps, and scratch files removed.
- [ ] No `.DS_Store`, `Thumbs.db`, or OS junk in repository.
- [ ] Universal `.editorconfig` present for line endings and indentation.
- [ ] Linters and formatters pass cleanly without blocking errors.
- [ ] No unfinished critical `TODO` or internal sensitive notes.

## 5. Build & Test Verification
- [ ] Project builds cleanly from source without missing dependencies.
- [ ] Test suite runs and passes 100%.
- [ ] Dependency lockfile (`pnpm-lock.yaml`, `package-lock.json`, `poetry.lock`, `Cargo.lock`) is in sync and committed.

## 6. Git & Repository Footprint
- [ ] Git repository initialized with appropriate default branch (`main`).
- [ ] No single file exceeds 50MB (GitHub warning) or 100MB (GitHub rejection).
- [ ] Large binary files, datasets, or model weights configured with Git LFS if needed.
- [ ] Clean working tree (`git status` shows no unexpected untracked files).
- [ ] Commit history is readable and free of accidental secret commits.

## 7. CI/CD & Automation
- [ ] CI workflow configured (e.g., `.github/workflows/ci.yml`).
- [ ] Automated dependency vulnerability scanning configured (e.g., Dependabot).
- [ ] Issue templates (`.github/ISSUE_TEMPLATE/`) configured.
- [ ] Pull request template (`.github/PULL_REQUEST_TEMPLATE.md`) configured.
