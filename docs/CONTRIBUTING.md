# Contributing to This Project

Thank you for your interest in contributing. This repository is a Spring Boot base template and enforces consistent code quality, formatting, and security standards across all services.

---

## Code Style Guidelines

### Java Formatting

- Java code **must** be formatted using **Google Java Format**.
- Formatting is enforced automatically using **Spotless**.
- Developers should not manually format code using IDE-specific styles that conflict with Spotless.

To automatically format code locally:

```shell
./gradlew spotlessApply
```

To verify formatting without modifying files:

```shell
./gradlew spotlessCheck
```

### Linting (Checkstyle)

- Java code is validated using **Checkstyle**.
- The Checkstyle configuration lives in:

```text
config/checkstyle/checkstyle.xml
```

- All Checkstyle rules must pass before code can be merged.
- Checkstyle does **not** auto-fix issues; it fails the build if violations are found.

To run Checkstyle manually:

```shell
./gradlew checkstyleMain
```

---

## Pre-commit Hook Requirements

This project uses **pre-commit** to enforce formatting, style, and security checks before commits are created.

### Required Setup

All contributors **must** install the pre-commit hooks locally:

```shell
pre-commit install
```

Once installed, the following checks run automatically on commit:

- Spotless code formatting (`spotlessApply`)
- Checkstyle validation
- Ministry of Justice DevSecOps baseline checks
- Secret scanning (Gitleaks)
- Merge conflict, large file, and private key detection

If a commit fails, follow the guidance in the output, fix the issues, and re-commit.

To run hooks manually on all files:

```shell
pre-commit run --all-files
```

---

## Testing and Code Coverage

- Unit and integration tests are executed using Gradle.
- Code coverage is collected using **JaCoCo**.

To run tests and generate a coverage report:

```shell
./gradlew test jacocoTestReport
```

Coverage reports are generated in:

```text
build/reports/jacoco/test/html/index.html
```

---

## Pull Request Checklist

Before raising a pull request, please ensure:

- [ ] Code builds successfully without errors
- [ ] All tests pass locally
- [ ] `./gradlew spotlessApply` has been run
- [ ] `./gradlew checkstyleMain` passes with no violations
- [ ] Pre-commit hooks pass successfully
- [ ] No secrets, credentials, or sensitive data are committed
- [ ] Documentation has been updated where relevant

Pull requests that do not meet these requirements may be rejected or returned for changes.

---

## Quality Expectations

This repository is intended to act as a **base template** for other services. Higher standards are therefore expected:

- Keep changes minimal and well-documented
- Avoid introducing unnecessary dependencies
- Prefer consistency with existing patterns over personal preference

Thank you for helping keep this template secure, consistent, and maintainable.
