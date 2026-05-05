## Contributing

Thank you for contributing to this repository. This document outlines the expectations and setup required to ensure contributions are consistent, secure, and easy to review.

### Local development setup

#### Prerequisites

Ensure you have the following installed:
- **Java 25 or 26** (supported versions for this project)
- Python 3
- Git
- pre-commit

Install pre-commit using pip:

```bash
pip install pre-commit - or (brew install pre-commit)
```

### Pre-commit hooks (required)

This repository uses **pre-commit** to run formatting, quality, and security checks before commits are created.

#### Installing hooks

After cloning the repository, you **must** run the install command:

```bash
pre-commit install
```

To confirm everything is configured correctly:

```bash
pre-commit run --all-files
```

### Code formatting and validation

#### Spotless (Java formatting)

Java code formatting is enforced using Spotless, executed via the Gradle wrapper.

- Runs automatically on every commit
- Modifies files in-place when formatting issues are found

To run manually:

```bash
./gradlew spotlessApply
```

#### Checkstyle

Checkstyle ensures Java code adheres to the project's coding standards.

To run manually:

```bash
./gradlew checkstyleStaged
```

### GitHub Actions security (enforced)

All GitHub Actions referenced in `.github/workflows/*.yml` files **must be pinned to a full 40-character commit SHA**.

This rule is enforced locally using the script:

```
scripts/check-github-actions-sha-pinning.sh
```

Any commit that introduces unpinned (tagged or branch-based) GitHub Actions will be **blocked**.

#### ✅ Allowed

```yaml
uses: actions/checkout@8f4b7c1e4c9fae9d7f3e45c9e4b8a9c0d1234567
```

#### ❌ Not allowed

```yaml
uses: actions/checkout@main
uses: actions/checkout@v4
```

### Quality gates (Definition of Done)

All contributions **must** meet the following quality criteria before they are considered complete:

- **Compilation**: The code compiles without errors and without warnings (`-Werror`).
- **Formatting**: `spotlessCheck` passes with no violations.
- **Coverage**: `jacocoTestReport` executes successfully.

### Troubleshooting

#### Pre-commit failures

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

### Pull request checklist

Before opening a pull request, ensure:

- [ ] `pre-commit run --all-files` passes
- [ ] No placeholder values remain in the code
- [ ] All Gradle tasks execute without errors
- [ ] Java code is formatted (Spotless)
- [ ] Checkstyle passes
- [ ] All GitHub Actions are SHA-pinned

Pull requests that do not meet these requirements may be blocked from merging.

Thank you for helping keep this project secure, readable, and maintainable.