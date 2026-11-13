# Contributing to {{PROJECT_NAME}}

Thank you for your interest in contributing to {{PROJECT_NAME}}! We value your time and efforts to improve this project.

## Development Workflow

1. **Fork & Branch:**
   - Fork the repository on GitHub.
   - Create a feature branch with a descriptive name:
     ```bash
     git checkout -b feat/your-feature-name
     # or: git checkout -b fix/issue-description
     ```

2. **Set Up Local Environment:**
   - Follow instructions in [README.md](README.md) to install dependencies.
   - Copy `.env.example` to `.env` and configure local variables.

3. **Code Style & Formatting:**
   - Adhere to the established code style and `.editorconfig` rules.
   - Run linters and formatters before committing changes.

4. **Testing Requirements:**
   - Add unit or integration tests for new features and bug fixes.
   - Ensure all existing tests pass:
     ```bash
     npm test # or pytest
     ```

5. **Commit Message Guidelines:**
   - Write clear, concise commit messages following Conventional Commits format:
     - `feat: add user authentication endpoint`
     - `fix: resolve race condition in worker pool`
     - `docs: update quickstart instructions`

6. **Submitting a Pull Request:**
   - Push your branch to your fork.
   - Open a Pull Request targeting the `main` branch.
   - Fill in the PR description template detailing your changes and referencing any related issues.

## Reporting Bugs

- Search existing issues to verify the bug has not already been reported.
- Open a new issue using the **Bug Report** template.
- Provide a minimal, reproducible example along with OS/runtime version details.

## Requesting Features

- Open a new issue using the **Feature Request** template.
- Explain the motivation, desired behavior, and potential alternatives.
