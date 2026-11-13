# Platform Feature & Path Mapping Matrix

Different Git hosting platforms use different conventions and directory structures for CI/CD, issue forms, and community health files.

| Feature | GitHub | GitLab | Bitbucket | Gitea / Forgejo |
| :--- | :--- | :--- | :--- | :--- |
| **Default Branch** | `main` | `main` | `main` or `master` | `main` |
| **CI/CD Config** | `.github/workflows/*.yml` | `.gitlab-ci.yml` | `bitbucket-pipelines.yml` | `.gitea/workflows/*.yml` |
| **Pull / Merge Request Template** | `.github/PULL_REQUEST_TEMPLATE.md` | `.gitlab/merge_request_templates/*.md` | `bitbucket-pipelines.yml` / Settings | `.gitea/pull_request_template.md` |
| **Issue Templates** | `.github/ISSUE_TEMPLATE/*.yml` | `.gitlab/issue_templates/*.md` | Settings | `.gitea/issue_template/*.md` |
| **Security Policy** | `SECURITY.md` or `.github/SECURITY.md` | `SECURITY.md` or `.gitlab/SECURITY.md` | `SECURITY.md` | `SECURITY.md` |
| **Contributing Guide** | `CONTRIBUTING.md` or `.github/` | `CONTRIBUTING.md` or `.gitlab/` | `CONTRIBUTING.md` | `CONTRIBUTING.md` |
| **Code of Conduct** | `CODE_OF_CONDUCT.md` or `.github/` | `CODE_OF_CONDUCT.md` or `.gitlab/` | `CODE_OF_CONDUCT.md` | `CODE_OF_CONDUCT.md` |
| **Automated Dep Updates** | `.github/dependabot.yml` | Dependency Scanning CI | Bitbucket Pipelines / Renovate | Renovate |
| **LFS Support** | `.gitattributes` | `.gitattributes` | `.gitattributes` | `.gitattributes` |
| **Max Single File Size** | 100 MB (Warns at 50 MB) | 100 MB (Default) | 100 MB (Default) | Configurable |
