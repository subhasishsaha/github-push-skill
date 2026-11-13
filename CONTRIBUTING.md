# Contributing to repo-publish-prep

Contributions to improve the auditing rules, stack-specific templates, or CI/CD pipelines are welcomed!

## Guidelines

1. **Bug fixes & Enhancements:** Open an issue first to discuss substantial additions.
2. **Testing:** Run the unit test suite before submitting:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
3. **Auditing:** Verify that the auditor itself passes:
   ```bash
   python skills/repo-publish-prep/scripts/audit_repo.py .
   ```
4. **Pull Requests:** Provide a clear description of changes in your pull request.
