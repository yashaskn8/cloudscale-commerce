# Release Procedure

This document explains the semantic versioning and release propagation model for CloudScale Commerce.

---

## 1. Branching Strategy

- **`main`**: Reflects production-ready code. Commits are tagged.
- **`develop`**: Integration branch for upcoming minor releases.
- **Feature Branches**: Feature work merged into `develop` via Pull Requests.

---

## 2. Versioning Rules

We adhere strictly to Semantic Versioning (`MAJOR.MINOR.PATCH`):
1. **MAJOR**: Breaking API contract changes (e.g. changing request payload properties).
2. **MINOR**: New backward-compatible features (e.g. adding a new query parameter).
3. **PATCH**: Backward-compatible bug fixes and security hotfixes.

---

## 3. Release Lifecycle

1. **Tagging**: Push a version tag to trigger GHA Release:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```
2. **Auto-Publishing**: GitHub Actions builds production Docker images, tags them with the release version, and publishes them to Amazon ECR.
3. **Deployment**: SRE triggers Helm release to EKS using the newly published image tag.
