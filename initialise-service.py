#!/usr/bin/env python3
"""
LAA Spring Boot Microservice Template — Initialisation Script
=============================================================
Renames all template placeholder values to your new service name across every
source file, renames the subproject directories, and restructures the README.
Optionally switches the database from H2 to PostgreSQL (RDS-ready).

Usage
-----
  python3 initialise-service.py                   # fully interactive
  python3 initialise-service.py laa-my-service    # skip the first prompt
  python3 initialise-service.py --dry-run         # preview only, no changes

Requirements: Python 3.9+, no third-party packages needed.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Template placeholder constants  — do NOT change these
# ─────────────────────────────────────────────────────────────────────────────
_T_ROOT_PROJECT   = "laa-spring-boot-microservice-template"
_T_KEBAB_FULL     = "laa-spring-boot-microservice"
_T_KEBAB          = "spring-boot-microservice"
_T_JAVA_PKG       = "uk.gov.justice.laa.springboot.microservice"
_T_GRADLE_PKG     = "uk.gov.laa.springboot.microservice"
_T_CLASS_PREFIX   = "SpringBootMicroservice"
_T_DISPLAY_NAME   = "LAA Spring Boot Microservice"
_T_SERVER_PORT    = "8081"
_T_MGMT_PORT      = "8181"
_T_VERSION        = "1.0.0"

# MoJ compliance badge URL base
_MOJ_BADGE_BASE = "https://github-community.service.justice.gov.uk/repository-standards"

# Fragment directory — contains postgres (and future feature) sub-directories.
# Excluded from all renaming/replacement walks.
_FRAGMENTS_DIR = Path(__file__).parent.resolve() / ".template-fragments"

# ─────────────────────────────────────────────────────────────────────────────
# Paths / files to skip
# ─────────────────────────────────────────────────────────────────────────────
_SKIP_DIRS = {
    ".git", ".gradle", "build", "bin", "generated", ".idea", "__pycache__",
    ".template-fragments",
}
_SKIP_FILES = {
    "gradlew", "gradlew.bat", "gradle-wrapper.jar",
    "initialise-service.py",
}
_SKIP_EXTS = {
    ".class", ".jar", ".exe", ".png", ".jpg", ".jpeg",
    ".svg", ".ico", ".bin", ".exec", ".gz", ".zip",
}

# ─────────────────────────────────────────────────────────────────────────────
# Java reserved keywords — warn if the derived package segment collides
# ─────────────────────────────────────────────────────────────────────────────
_JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while",
}


# ─────────────────────────────────────────────────────────────────────────────
# Derivation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _strip_laa(name: str) -> str:
    """'laa-my-service' -> 'my-service'"""
    return re.sub(r"^laa-", "", name)


def _to_pascal(kebab: str) -> str:
    """'my-service' -> 'MyService'"""
    return "".join(w.capitalize() for w in kebab.split("-"))


def _to_pkg(kebab: str) -> str:
    """'my-service' -> 'my.service'"""
    return re.sub(r"[^a-z0-9.]", ".", kebab.lower())


def _to_display(kebab: str) -> str:
    """'my-service' -> 'LAA My Service'"""
    return "LAA " + " ".join(w.capitalize() for w in kebab.split("-"))


# ─────────────────────────────────────────────────────────────────────────────
# Prompting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prompt(question: str, default: str = "", required: bool = False) -> str:
    hint = f" [{default}]" if default else ""
    while True:
        try:
            answer = input(f"  {question}{hint}: ").strip()
        except EOFError:
            return default
        if answer:
            return answer
        if default:
            return default
        if not required:
            return ""
        print("    ✖  This field is required.\n")


def _prompt_yn(question: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        answer = input(f"  {question} [{hint}]: ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in ("y", "yes")


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate(service_name: str, pkg_suffix: str, class_prefix: str) -> list[str]:
    errors = []
    if not re.match(r"^[a-z][a-z0-9-]*$", service_name):
        errors.append(
            f"Service name '{service_name}' must be lowercase kebab-case "
            "(e.g. laa-my-service)."
        )
    for seg in pkg_suffix.split("."):
        if not seg:
            errors.append(f"Package suffix '{pkg_suffix}' contains an empty segment.")
        elif not re.match(r"^[a-z][a-z0-9_]*$", seg):
            errors.append(
                f"Package segment '{seg}' is not a valid Java identifier."
            )
        elif seg in _JAVA_KEYWORDS:
            errors.append(
                f"Package segment '{seg}' is a Java reserved keyword — "
                "use --package-suffix to override."
            )
    if not re.match(r"^[A-Z][A-Za-z0-9]*$", class_prefix):
        errors.append(
            f"Class prefix '{class_prefix}' must start with an uppercase letter "
            "and contain only alphanumeric characters (e.g. MyService)."
        )
    return errors


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────

def _should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in _SKIP_DIRS:
            return True
    if path.name in _SKIP_FILES:
        return True
    if path.suffix in _SKIP_EXTS:
        return True
    return False


def _replace_in_file(
    path: Path,
    replacements: list[tuple[str, str]],
    dry_run: bool,
) -> bool:
    """Apply all substitutions to a file. Returns True if content changed."""
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError) as exc:
        print(f"    WARNING: skipping {path.name} — {exc}")
        return False

    updated = original
    for old, new in replacements:
        updated = updated.replace(old, new)

    if updated == original:
        return False
    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return True


def _remove_empty_parents(path: Path, stop_at: Path):
    current = path
    while current != stop_at:
        try:
            current.rmdir()
            current = current.parent
        except OSError:
            break


# ─────────────────────────────────────────────────────────────────────────────
# Port replacement — targeted at specific files only to avoid false positives
# ─────────────────────────────────────────────────────────────────────────────

def _apply_port_replacements(
    root: Path,
    service_name: str,
    old_server: str,
    new_server: str,
    old_mgmt: str,
    new_mgmt: str,
    dry_run: bool,
):
    """Replace port numbers in the files where we know they live."""
    if old_server == new_server and old_mgmt == new_mgmt:
        return

    # application.yml  ─ replace "port: NNNN" to be safe
    app_yml = (
        root / f"{service_name}-service" / "src" / "main" / "resources" / "application.yml"
    )
    # Before renaming, the path still uses the template name — handle both
    if not app_yml.exists():
        app_yml = (
            root / f"{_T_KEBAB}-service" / "src" / "main" / "resources" / "application.yml"
        )

    _targeted_replace(app_yml, [
        (f"port: {old_server}", f"port: {new_server}"),
        (f"port: {old_mgmt}",   f"port: {new_mgmt}"),
    ], dry_run)

    # Dockerfile  ─ EXPOSE and port in JAR copy path
    _targeted_replace(root / "Dockerfile", [
        (f"EXPOSE {old_server} {old_mgmt}", f"EXPOSE {new_server} {new_mgmt}"),
    ], dry_run)

    # docker-compose.yml
    _targeted_replace(root / "docker-compose.yml", [
        (f'"{old_server}:{old_server}"', f'"{new_server}:{new_server}"'),
        (f'"{old_mgmt}:{old_mgmt}"',     f'"{new_mgmt}:{new_mgmt}"'),
    ], dry_run)

    # README.md  ─ update localhost example URLs
    _targeted_replace(root / "README.md", [
        (f"localhost:{old_server}", f"localhost:{new_server}"),
    ], dry_run)


def _targeted_replace(path: Path, pairs: list[tuple[str, str]], dry_run: bool):
    if not path.exists():
        return
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return
    updated = original
    for old, new in pairs:
        updated = updated.replace(old, new)
    if updated != original:
        if not dry_run:
            path.write_text(updated, encoding="utf-8")
        print(f"    Updated ports in : {path.name}")


# ─────────────────────────────────────────────────────────────────────────────
# README cleanup — strip template-only content after renaming
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_readme(root: Path, service_name: str, dry_run: bool):
    """
    After the standard name replacements have run, tidy up the README:
      1. Remove the '⚠️ WORK IN PROGRESS ⚠️' section.
      2. Replace the 'Setup Instructions' section (now done by this script)
         with a short TODO block so developers know to rewrite it.
    """
    readme = root / "README.md"
    if not readme.exists():
        return
    try:
        content = readme.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return

    updated = content

    # 1. Remove WIP banner (the ### heading + its paragraph)
    updated = re.sub(
        r"### ⚠️ WORK IN PROGRESS ⚠️\n.*?\n\n",
        "",
        updated,
        flags=re.DOTALL,
    )

    # 2. Replace 'Setup Instructions' section with a TODO placeholder.
    #    The section runs from '## Setup Instructions' up to (not including)
    #    '### Database scripts'.
    updated = re.sub(
        r"## Setup Instructions\n.*?(?=### Database scripts)",
        (
            "## TODO: Update this README\n\n"
            "Replace this section with clear documentation for your service. "
            "Include what it does, how to run it locally, environment variables, "
            "and any other details relevant to developers.\n\n"
        ),
        updated,
        flags=re.DOTALL,
    )

    if updated != content:
        if not dry_run:
            readme.write_text(updated, encoding="utf-8")
        print("    Cleaned up       : README.md (removed WIP banner + setup instructions)")


# ─────────────────────────────────────────────────────────────────────────────
# Main steps
# ─────────────────────────────────────────────────────────────────────────────

def _section(title: str):
    print(f"\n{'─' * 65}")
    print(f"  {title}")
    print("─" * 65)


def step_update_contents(
    root: Path,
    replacements: list[tuple[str, str]],
    dry_run: bool,
):
    _section("Step 1 / 4  —  Updating file contents")
    changed = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if _should_skip(fpath):
                continue
            if _replace_in_file(fpath, replacements, dry_run):
                print(f"    Updated  : {fpath.relative_to(root)}")
                changed += 1
    print(f"\n    {changed} file(s) updated.")


def step_rename_java_files(
    root: Path,
    old_prefix: str,
    new_prefix: str,
    dry_run: bool,
):
    _section("Step 2 / 4  —  Renaming Java source files")
    targets = [
        (f"{old_prefix}Application.java",      f"{new_prefix}Application.java"),
        (f"{old_prefix}ApplicationTests.java",  f"{new_prefix}ApplicationTests.java"),
    ]
    found = False
    for old_name, new_name in targets:
        for match in root.rglob(old_name):
            if _should_skip(match):
                continue
            new_path = match.parent / new_name
            print(f"    Rename   : {match.relative_to(root)}")
            print(f"           →   {new_path.relative_to(root)}")
            if not dry_run:
                match.rename(new_path)
            found = True
    if not found:
        print("    Nothing to rename.")


def step_rename_pkg_dirs(
    root: Path,
    old_java_pkg: str,
    new_java_pkg: str,
    dry_run: bool,
):
    _section("Step 3 / 4  —  Renaming Java package directories")
    old_rel = Path(old_java_pkg.replace(".", os.sep))
    new_rel = Path(new_java_pkg.replace(".", os.sep))

    found = False
    for java_dir in root.rglob("java"):
        if _should_skip(java_dir) or not java_dir.is_dir():
            continue
        old_pkg_dir = java_dir / old_rel
        if not old_pkg_dir.exists():
            continue
        new_pkg_dir = java_dir / new_rel
        print(f"    Rename   : {old_pkg_dir.relative_to(root)}")
        print(f"           →   {new_pkg_dir.relative_to(root)}")
        if not dry_run:
            new_pkg_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_pkg_dir), str(new_pkg_dir))
            _remove_empty_parents(old_pkg_dir.parent, stop_at=java_dir)
        found = True
    if not found:
        print("    Nothing to rename.")


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL step — applies fragments from .template-fragments/postgres/
# ─────────────────────────────────────────────────────────────────────────────

def step_configure_postgres(
    root: Path,
    service_name: str,
    new_java_pkg: str,
    server_port: str,
    mgmt_port: str,
    dry_run: bool,
):
    """
    Switches the service from H2 to PostgreSQL (RDS-ready) by:
      1. Replacing the H2 runtimeOnly dep with postgresql + flyway in build.gradle
      2. Adding testcontainers deps (replacing H2 in tests)
      3. Replacing the datasource block in application.yml with env-var-driven config
      4. Converting schema.sql / data.sql to Flyway migrations under db/migration/
      5. Adding a postgres service to docker-compose.yml and DB env vars to the app service
      6. Copying a TestcontainersConfig.java into the integration test source tree
      7. Creating a .helm/ directory with Chart.yaml (depending on laa-generic-helm-chart)
         and per-environment values files — DB env vars read from the
         rds-postgresql-instance-output Kubernetes Secret created by Cloud Platform
    All fragment files live in .template-fragments/postgres/ and contain %%TOKEN%%
    placeholders that are substituted with the user's chosen values before writing.
    """
    _section("Step 5 / 5  —  Configuring PostgreSQL (RDS-ready)")

    pg_dir = _FRAGMENTS_DIR / "postgres"

    # Token substitutions applied to every fragment before it is written.
    # %%SERVICE_KEBAB%% → service name without laa- prefix (used as DB name, container name)
    # %%JAVA_PKG%%      → full Java package (for TestcontainersConfig)
    # %%SERVER_PORT%%   → server port (for helm values)
    # %%MGMT_PORT%%     → management port (for helm values)
    core = re.sub(r"^laa-", "", service_name)
    tokens = {
        "%%SERVICE_KEBAB%%": core,
        "%%JAVA_PKG%%":      new_java_pkg,
        "%%SERVER_PORT%%":   server_port,
        "%%MGMT_PORT%%":     mgmt_port,
    }

    def _fill(text: str) -> str:
        for tok, val in tokens.items():
            text = text.replace(tok, val)
        return text

    def _write(dest: Path, text: str):
        if dry_run:
            print(f"    Would write  : {dest.relative_to(root)}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            print(f"    Written      : {dest.relative_to(root)}")

    def _fragment(name: str) -> str:
        return _fill((pg_dir / name).read_text(encoding="utf-8"))

    # ── Locate the service subproject (may already be renamed) ────────────────
    service_dir = root / f"{service_name}-service"
    if not service_dir.exists():
        service_dir = root / f"{_T_KEBAB}-service"

    # ── 1. build.gradle — replace H2 with postgresql + flyway ─────────────────
    build_gradle = service_dir / "build.gradle"
    if build_gradle.exists():
        original = build_gradle.read_text(encoding="utf-8")
        updated = original.replace(
            "    runtimeOnly 'com.h2database:h2'",
            _fragment("build-gradle-additions.txt").rstrip(),
        )
        # Inject testcontainers deps before the closing brace of the test block
        updated = updated.replace(
            "    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'",
            _fragment("build-gradle-test-additions.txt").rstrip()
            + "\n\n    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'",
        )
        if updated != original:
            if not dry_run:
                build_gradle.write_text(updated, encoding="utf-8")
            print(f"    Updated      : {build_gradle.relative_to(root)}")
        else:
            print("    WARNING: could not patch build.gradle — check manually")

    # ── 2. application.yml — replace datasource + jpa block ───────────────────
    app_yml = service_dir / "src" / "main" / "resources" / "application.yml"
    if app_yml.exists():
        original = app_yml.read_text(encoding="utf-8")
        # Replace from "  # example database" through the jpa block (end of ddl-auto line)
        updated = re.sub(
            r" {2}# example database\n {2}datasource:.*?ddl-auto: none",
            _fragment("application-datasource.yml").rstrip(),
            original,
            flags=re.DOTALL,
        )
        if updated != original:
            if not dry_run:
                app_yml.write_text(updated, encoding="utf-8")
            print(f"    Updated      : {app_yml.relative_to(root)}")
        else:
            print("    WARNING: could not patch application.yml — check manually")

    # ── 3. Flyway migrations — replace schema.sql / data.sql ──────────────────
    resources_dir = service_dir / "src" / "main" / "resources"
    migration_dir = resources_dir / "db" / "migration"

    schema_sql = resources_dir / "schema.sql"
    data_sql   = resources_dir / "data.sql"

    _write(migration_dir / "V1__create_items_table.sql", _fragment("V1__create_items_table.sql"))
    _write(migration_dir / "V2__seed_items.sql",         _fragment("V2__seed_items.sql"))

    for old_file in (schema_sql, data_sql):
        if old_file.exists():
            if dry_run:
                print(f"    Would delete : {old_file.relative_to(root)}")
            else:
                old_file.unlink()
                print(f"    Deleted      : {old_file.relative_to(root)}")

    # ── 4. docker-compose.yml — add postgres service + DB env vars ────────────
    compose_file = root / "docker-compose.yml"
    if compose_file.exists():
        original = compose_file.read_text(encoding="utf-8")
        postgres_service = _fragment("docker-compose-postgres.yml")
        app_env_vars     = _fragment("docker-compose-app-env.yml")

        # Prepend the postgres service before the app service
        updated = original.replace("services:\n", "services:\n" + postgres_service + "\n")

        # Add depends_on + DB env vars to the app service environment block.
        # Insert after "environment:" if it exists, otherwise append to app service.
        updated = updated.replace(
            "    environment:\n      - SERVER_PORT=",
            "    depends_on:\n      postgres:\n        condition: service_healthy\n"
            "    environment:\n" + app_env_vars
            + "      - SERVER_PORT=",
        )
        if updated != original:
            if not dry_run:
                compose_file.write_text(updated, encoding="utf-8")
            print(f"    Updated      : {compose_file.relative_to(root)}")
        else:
            print("    WARNING: could not patch docker-compose.yml — check manually")

    # ── 5. TestcontainersConfig.java ───────────────────────────────────────────
    pkg_path = new_java_pkg.replace(".", os.sep)
    tc_dest = (
        service_dir / "src" / "integrationTest" / "java" / pkg_path / "TestcontainersConfig.java"
    )
    _write(tc_dest, _fragment("TestcontainersConfig.java"))

    # ── 6. Patch ItemControllerIntegrationTest to import TestcontainersConfig ──
    it_file = (
        service_dir / "src" / "integrationTest" / "java" / pkg_path / "controller"
        / "ItemControllerIntegrationTest.java"
    )
    if it_file.exists():
        original = it_file.read_text(encoding="utf-8")
        import_line = f"import {new_java_pkg}.TestcontainersConfig;\n"
        spring_import = "import org.springframework.context.annotation.Import;\n"
        updated = original
        if import_line not in updated:
            updated = updated.replace(
                "@SpringBootTest(",
                spring_import + import_line + "\n@Import(TestcontainersConfig.class)\n@SpringBootTest(",
            )
        if updated != original:
            if not dry_run:
                it_file.write_text(updated, encoding="utf-8")
            print(f"    Updated      : {it_file.relative_to(root)}")

    # ── 7. Helm chart ──────────────────────────────────────────────────────────
    helm_root = root / ".helm" / service_name
    src_helm  = pg_dir / "helm"

    for src_file in src_helm.rglob("*"):
        if src_file.is_file():
            rel      = src_file.relative_to(src_helm)
            dest     = helm_root / rel
            _write(dest, _fill(src_file.read_text(encoding="utf-8")))

    print("\n    PostgreSQL configuration complete.")
    print(f"    Helm chart skeleton written to .helm/{service_name}/")
    print(f"    Run 'helm dependency update .helm/{service_name}' before deploying.")


def step_rename_subproject_dirs(
    root: Path,
    old_kebab: str,
    new_kebab: str,
    dry_run: bool,
):
    _section("Step 4 / 4  —  Renaming subproject directories")
    found = False
    for suffix in ("-api", "-service"):
        old_dir = root / f"{old_kebab}{suffix}"
        new_dir = root / f"{new_kebab}{suffix}"
        if old_dir.exists() and old_dir != new_dir:
            print(f"    Rename   : {old_dir.name}  →  {new_dir.name}")
            if not dry_run:
                old_dir.rename(new_dir)
            found = True
    if not found:
        print("    Nothing to rename.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Initialise a new LAA service from the spring-boot-microservice template.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 initialise-service.py\n"
            "  python3 initialise-service.py laa-crime-applications\n"
            "  python3 initialise-service.py laa-crime-applications --dry-run\n"
        ),
    )
    parser.add_argument(
        "service_name",
        nargs="?",
        help="New service name in kebab-case, e.g. laa-crime-applications",
    )
    parser.add_argument(
        "--package-suffix",
        metavar="PKG",
        help="Override the Java package suffix, e.g. crime.applications",
    )
    parser.add_argument(
        "--class-prefix",
        metavar="CLS",
        help="Override the Application class prefix, e.g. CrimeApplications",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all changes without modifying any files.",
    )
    args = parser.parse_args()

    # ── Banner ────────────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  LAA Spring Boot Microservice Template  —  Initialisation")
    print("=" * 65)
    if args.dry_run:
        print("\n  *** DRY RUN — no files will be modified ***")
    print()

    # ── Collect inputs ────────────────────────────────────────────────────────

    # 1. Service name (required)
    if args.service_name:
        service_name = args.service_name.lower().strip()
    else:
        service_name = _prompt(
            "New service name (kebab-case, e.g. laa-crime-applications)",
            required=True,
        ).lower()

    core_name    = _strip_laa(service_name)          # e.g. crime-applications
    new_full     = f"laa-{core_name}"                # always laa-prefixed

    # 2. Java package suffix
    default_pkg = _to_pkg(core_name)
    if args.package_suffix:
        pkg_suffix = args.package_suffix
    else:
        pkg_suffix = _prompt(
            "Java package suffix (dot-notation)",
            default=default_pkg,
        ) or default_pkg

    # 3. Application class prefix
    default_cls = _to_pascal(core_name)
    if args.class_prefix:
        class_prefix = args.class_prefix
    else:
        class_prefix = _prompt(
            "Application class prefix (PascalCase)",
            default=default_cls,
        ) or default_cls

    # 4. Application version
    version = _prompt(
        "Application version (gradle.properties)",
        default=_T_VERSION,
    ) or _T_VERSION

    # 5. Server port
    server_port = _prompt(
        "Server port (application.yml / Dockerfile)",
        default=_T_SERVER_PORT,
    ) or _T_SERVER_PORT

    # 6. Management port
    mgmt_port = _prompt(
        "Management (actuator) port",
        default=_T_MGMT_PORT,
    ) or _T_MGMT_PORT

    # 7. Self-delete
    self_delete = _prompt_yn(
        "Delete this initialisation script once complete?",
        default=False,
    )

    # 8. Database choice
    use_postgres = _prompt_yn(
        "Use PostgreSQL instead of H2? (RDS-ready — adds Flyway, Testcontainers, helm chart)",
        default=False,
    )

    # ── Validate ──────────────────────────────────────────────────────────────
    errors = _validate(service_name, pkg_suffix, class_prefix)
    if not server_port.isdigit() or not (1 <= int(server_port) <= 65535):
        errors.append(f"Server port '{server_port}' is not a valid port number.")
    if not mgmt_port.isdigit() or not (1 <= int(mgmt_port) <= 65535):
        errors.append(f"Management port '{mgmt_port}' is not a valid port number.")

    if errors:
        print("\n  ERROR — invalid input(s):\n")
        for e in errors:
            print(f"    ✖  {e}")
        print()
        sys.exit(1)

    new_java_pkg    = f"uk.gov.justice.laa.{pkg_suffix}"
    new_gradle_pkg  = f"uk.gov.laa.{pkg_suffix}"
    display_name    = _to_display(core_name)

    # ── Confirmation summary ──────────────────────────────────────────────────
    print()
    print("┌" + "─" * 63 + "┐")
    print("│  Please review the values below before proceeding.           │")
    print("├" + "─" * 63 + "┤")
    rows = [
        ("Service name",      service_name),
        ("Root project name", new_full),
        ("Subproject dirs",   f"{new_full}-api  /  {new_full}-service"),
        ("Java package",      new_java_pkg),
        ("Application class", f"{class_prefix}Application"),
        ("Display name",      display_name),
        ("Version",           version),
        ("Server port",       server_port),
        ("Management port",   mgmt_port),
        ("Delete script",     "yes" if self_delete else "no"),
        ("Database",          "PostgreSQL (RDS)" if use_postgres else "H2 (in-memory)"),
        ("Dry run",           "yes" if args.dry_run else "no"),
    ]
    for label, value in rows:
        print(f"│  {label:<22} {value:<38} │")
    print("└" + "─" * 63 + "┘")
    print()

    if not _prompt_yn("Proceed with these values?", default=False):
        print("\n  Aborted — no changes were made.\n")
        sys.exit(0)

    # ── Build content replacement table (ORDER IS CRITICAL) ──────────────────
    #
    #  Replace most-specific strings first so shorter patterns don't partially
    #  clobber them.  For example, 'laa-spring-boot-microservice-template' must
    #  be replaced before 'laa-spring-boot-microservice', which in turn must be
    #  replaced before 'spring-boot-microservice'.
    #
    content_replacements: list[tuple[str, str]] = [
        (_T_ROOT_PROJECT,   new_full),                  # settings.gradle, README badge
        (_T_KEBAB_FULL,     new_full),                  # Dockerfile, workflow docker tag
        (_T_KEBAB,          service_name),              # module names, gradle paths
        (_T_JAVA_PKG,       new_java_pkg),              # Java package decls + imports
        (_T_GRADLE_PKG,     new_gradle_pkg),            # dependabot.yml groups
        (_T_CLASS_PREFIX,   class_prefix),              # class names, jacoco exclusions
        (_T_DISPLAY_NAME,   display_name),              # application.yml spring.application.name
    ]

    # Version replacement is targeted to gradle.properties only
    # (avoid replacing '1.0.0' appearing in unrelated places)
    if version != _T_VERSION:
        content_replacements.append((f"version={_T_VERSION}", f"version={version}"))

    root = Path(__file__).parent.resolve()

    # ── Execute ───────────────────────────────────────────────────────────────
    step_update_contents(root, content_replacements, args.dry_run)
    step_rename_java_files(root, _T_CLASS_PREFIX, class_prefix, args.dry_run)
    step_rename_pkg_dirs(root, _T_JAVA_PKG, new_java_pkg, args.dry_run)
    step_rename_subproject_dirs(root, _T_KEBAB, service_name, args.dry_run)

    # Port replacements run after directory renames (paths have changed)
    if server_port != _T_SERVER_PORT or mgmt_port != _T_MGMT_PORT:
        _section("Updating port numbers")
        _apply_port_replacements(
            root, service_name,
            _T_SERVER_PORT, server_port,
            _T_MGMT_PORT,   mgmt_port,
            args.dry_run,
        )

    # README cleanup — strip WIP banner and setup instructions
    _section("Cleaning up README")
    _cleanup_readme(root, service_name, args.dry_run)

    # PostgreSQL configuration (optional)
    if use_postgres:
        step_configure_postgres(
            root, service_name, new_java_pkg,
            server_port, mgmt_port,
            args.dry_run,
        )

    # ── Done ──────────────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    if args.dry_run:
        print("  DRY RUN complete — no files were modified.")
        print("  Re-run without --dry-run to apply changes.")
    else:
        print(f"  ✓  Initialisation complete for '{service_name}'!")
        pg_steps = ""
        if use_postgres:
            pg_steps = """
  8.  .helm/                    Run: helm dependency update .helm/%%SERVICE_KEBAB%%
                                Set image.registry + image.repository in each values file
                                Cloud Platform provisions the rds-postgresql-instance-output
                                secret automatically when the RDS module is applied
  9.  TestcontainersConfig      Docker must be running for integration tests to pass"""
        print(f"""
  Remaining manual steps
  ──────────────────────────────────────────────────────────
  1.  git diff                  Review every change before committing
  2.  README.md                 Rewrite the TODO section for your service
  3.  open-api-specification.yml  Replace with your own API design
  4.  application.yml           Set sentry.dsn and sentry.environment
  5.  dependabot.yml            Uncomment and configure the registries section
  6.  .github/CODEOWNERS        Set your team as code owner
  7.  Remove example domain     Delete Item* classes, schema.sql, data.sql
                                if you don't need them{pg_steps}
  ──────────────────────────────────────────────────────────""")

    if self_delete and not args.dry_run:
        try:
            Path(__file__).unlink()
            print("  ✓  Script deleted.")
        except OSError as exc:
            print(f"  WARNING: Could not delete script — {exc}")

    print("=" * 65)
    print()


if __name__ == "__main__":
    main()

