# Secrets Remediation Runbook

When a secret, credential, private key, or `.env` file is accidentally committed or staged in Git, follow this emergency response protocol immediately.

> [!CAUTION]
> **Cardinal Rule of Secret Leaks:** Once a secret has been pushed to a remote repository or public branch, consider it permanently compromised. Simply committing a fix or deleting the file in a new commit does **NOT** protect you — the secret remains in the Git commit history and can be easily retrieved with `git log` or commit scraping bots.

---

## Emergency Protocol: 3 Steps

### Step 1: Revoke & Rotate the Compromised Credential (Immediate)
Before altering Git history, invalidate the credential at the provider:
- **Cloud Providers (AWS, GCP, Azure):** Delete the IAM access key; rotate the service account key.
- **API Keys (OpenAI, Gemini, Stripe, Anthropic):** Invalidate the compromised key in your developer dashboard and generate a fresh key.
- **Tokens (GitHub, GitLab, Slack):** Revoke the personal access token or app token immediately.
- **Databases:** Change database user passwords and verify connection logs for unauthorized access.

---

### Step 2: Remove the Secret from Git

#### Scenario A: Secret is modified or untracked (Not Yet Committed)
If the secret is only in your working tree or staged:
```bash
# Unstage the sensitive file
git reset HEAD <path/to/sensitive/file>

# Add to .gitignore
echo "<path/to/sensitive/file>" >> .gitignore

# Verify git status shows it ignored
git status
```

#### Scenario B: Secret was committed locally (Not Yet Pushed)
If the secret was committed in recent unpushed commits:
```bash
# If it was the very last commit:
# 1. Untrack the file
git rm --cached <path/to/sensitive/file>
echo "<path/to/sensitive/file>" >> .gitignore
git add .gitignore

# 2. Amend the commit without the sensitive file
git commit --amend --no-edit
```

#### Scenario C: Secret was already pushed to remote (History Rewrite Required)
Use `git-filter-repo` (the modern, official Git-recommended tool) to permanently eradicate the file from all commits and branches:

1. Install `git-filter-repo`:
   ```bash
   pip install git-filter-repo
   ```

2. Make a fresh backup clone of your repository:
   ```bash
   git clone --mirror <repo-url> repo-backup.git
   ```

3. Strip the file from all commits:
   ```bash
   git filter-repo --path <path/to/sensitive/file> --invert-paths
   ```

4. Force-push to all remote branches:
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

---

## Proactive Prevention Tools

Set up automated pre-commit hooks to block secrets from ever entering a commit:
1. **Gitleaks:**
   ```bash
   # Run gitleaks locally
   gitleaks detect --source . -v
   ```
2. **Pre-commit framework:**
   Add `detect-secrets` or `gitleaks` hook to `.pre-commit-config.yaml`.
