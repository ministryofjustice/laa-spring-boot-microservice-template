# Contributing

Thank you for contributing to this repository. This document outlines the expectations and setup required to ensure contributions are consistent, secure, and easy to review.

---

## Local development setup

### Prerequisites

Ensure you have the following installed:

- A supported Java version for this project
- Python 3
- `pre-commit`
- Git

Install `pre-commit` using pip:

```bash
pip install pre-commit
```

---

## Pre-commit hooks (required)

This repository uses **pre-commit** to run formatting, quality, and security checks before commits are created.

### Installing hooks

After cloning the repository, run:

```bash
pre-commit install
```

To confirm everything is configured correctly:

```bash
pre-commit run --all-files
```

---

## Code formatting and validation

### Spotless (Java formatting)

Java code formatting is enforced using Spotless, executed via the Gradle wrapper.

- Runs automatically on every commit
- Modifies files in-place when formatting issues are found

To run manually:

```bash
./gradlew spotlessApply
```

---

### Checkstyle

Checkstyle ensures Java code adheres to the project's coding standards.

To run manually:

```bash
./gradlew checkstyleStaged
```

---

## GitHub Actions security requirements

### SHA pinning (enforced)

All GitHub Actions referenced in `.github/workflows/*.yml` files **must be pinned to full-length commit SHAs**.

#### ✅ Allowed

```yaml
uses: actions/checkout@8f4b7c1e4c9fae9d7f3e45c9e4b8a9c0d1234567
```

#### ❌ Not allowed

```yaml
uses: actions/checkout@main
uses: actions/checkout@v4
```

This rule is enforced locally using a pre-commit hook:

```text
scripts/check-github-actions-sha-pinning.sh
```

Commits that introduce unpinned actions will fail.

---

## Adding or updating GitHub Actions

When adding or updating GitHub Actions:

1. Identify the exact commit SHA to use
2. Update the workflow to reference that SHA
3. Run the SHA pinning hook:

```bash
pre-commit run github-actions-sha-pinning
```

4. Commit the change

---

## Troubleshooting

### Pre-commit failures

If a pre-commit hook fails:

- Read the error output — most failures explain how to fix the issue
- Formatting hooks may automatically update files; re-commit if changes occur
- Re-run an individual hook if needed:

```bash
pre-commit run <hook-id>
```

If hooks appear misconfigured:

```bash
pre-commit clean
pre-commit install
```

---

## Pull request checklist

Before opening a pull request, ensure:

- `pre-commit run --all-files` passes
- Java code is formatted (Spotless)
- Checkstyle passes
- All GitHub Actions are SHA-pinned
- No placeholder values or floating references remain

Pull requests that do not meet these requirements may be blocked from merging.

---

Thank you for helping keep this project secure, readable, and maintainable.
