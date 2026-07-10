# Contributing to CloudScale Commerce

We welcome contributions to CloudScale! Please follow these guidelines to submit pull requests and maintain engineering quality.

---

## Code Style & Formatting

1. **Python Formatting**: All code must conform to Black styling (120 char line-limit).
   - Format: `black services/shared`
2. **Linting**: Ruff is used for general static checking. Ensure zero lint errors before pushing.
3. **Type Hints**: Explicit typing is required on all public methods and route endpoints. MyPy checks must pass.

## Branching & Commit Conventions

- Use feature branches: `feature/short-description` or `bugfix/issue-id`.
- Follow Conventional Commits:
  - `feat(order): add invoice generation outbox flow`
  - `fix(auth): correct token rotation expiry checking`
  - `docs(readme): update helm installation instructions`

## Submitting Pull Requests

1. Run all tests locally first:
   ```bash
   pytest
   ```
2. Open a PR targeting `develop` or `main`.
3. Verify that the GitHub Actions PR Validation pipeline completes successfully.
