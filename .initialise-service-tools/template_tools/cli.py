"""
Command-line entry point — argument parsing, prompting, and orchestration.
"""
import shutil
import sys
from pathlib import Path

from .constants import (
    _T_ROOT_PROJECT, _T_KEBAB_FULL, _T_KEBAB,
    _T_JAVA_PKG, _T_GRADLE_PKG, _T_CLASS_PREFIX, _T_DISPLAY_NAME,
    _T_SERVER_PORT, _T_MGMT_PORT, _T_VERSION,
    _FRAGMENTS_DIR,
)
from .helpers import strip_laa, to_pascal, to_pkg, to_display, prompt, prompt_yn, validate, section
from .steps import (
    step_update_contents,
    step_rename_java_files,
    step_rename_pkg_dirs,
    step_rename_subproject_dirs,
    step_apply_port_replacements,
    step_cleanup_readme,
)
from .postgres import step_configure_postgres


def main(args=None) -> None:
    import argparse
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
    parser.add_argument("service_name", nargs="?",
                        help="New service name in kebab-case, e.g. laa-crime-applications")
    parser.add_argument("--package-suffix", metavar="PKG",
                        help="Override the Java package suffix, e.g. crime.applications")
    parser.add_argument("--class-prefix", metavar="CLS",
                        help="Override the Application class prefix, e.g. CrimeApplications")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview all changes without modifying any files.")
    parsed = parser.parse_args(args)

    print()
    print("=" * 65)
    print("  LAA Spring Boot Microservice Template  —  Initialisation")
    print("=" * 65)
    if parsed.dry_run:
        print("\n  *** DRY RUN — no files will be modified ***")
    print()

    if parsed.service_name:
        service_name = parsed.service_name.lower().strip()
    else:
        service_name = prompt(
            "New service name (kebab-case, e.g. laa-crime-applications)", required=True
        ).lower()

    core_name = strip_laa(service_name)
    new_full  = f"laa-{core_name}"

    default_pkg  = to_pkg(core_name)
    pkg_suffix   = parsed.package_suffix or prompt("Java package suffix (dot-notation)", default=default_pkg) or default_pkg

    default_cls  = to_pascal(core_name)
    class_prefix = parsed.class_prefix or prompt("Application class prefix (PascalCase)", default=default_cls) or default_cls

    version     = prompt("Application version (gradle.properties)", default=_T_VERSION) or _T_VERSION
    server_port = prompt("Server port (application.yml / Dockerfile)", default=_T_SERVER_PORT) or _T_SERVER_PORT
    mgmt_port   = prompt("Management (actuator) port", default=_T_MGMT_PORT) or _T_MGMT_PORT
    self_delete = prompt_yn("Delete this initialisation script and associated template fragments once complete?", default=False)
    use_postgres = prompt_yn("Use PostgreSQL instead of H2? (RDS-ready — adds Flyway, Testcontainers, helm chart)", default=False)

    errors = validate(service_name, pkg_suffix, class_prefix)
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

    new_java_pkg   = f"uk.gov.justice.laa.{pkg_suffix}"
    new_gradle_pkg = f"uk.gov.laa.{pkg_suffix}"
    display_name   = to_display(core_name)

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
        ("Delete init files", "yes" if self_delete else "no"),
        ("Database",          "PostgreSQL (RDS)" if use_postgres else "H2 (in-memory)"),
        ("Dry run",           "yes" if parsed.dry_run else "no"),
    ]
    label_width  = max(max(len(l) for l, _ in rows), 22)
    value_width  = max(max(len(v) for _, v in rows), 38)
    inner_width  = max(2 + label_width + 1 + value_width + 1,
                       len("  Please review the values below before proceeding."))
    heading = "Please review the values below before proceeding."
    print()
    print("┌" + "─" * inner_width + "┐")
    print(f"│{('  ' + heading):<{inner_width}}│")
    print("├" + "─" * inner_width + "┤")
    for label, value in rows:
        row_text = f"  {label:<{label_width}} {value:<{value_width}}"
        print(f"│{row_text:<{inner_width}}│")
    print("└" + "─" * inner_width + "┘")
    print()

    if not prompt_yn("Proceed with these values?", default=False):
        print("\n  Aborted — no changes were made.\n")
        sys.exit(0)

    content_replacements: list[tuple[str, str]] = [
        (_T_ROOT_PROJECT,  new_full),
        (_T_KEBAB_FULL,    new_full),
        (_T_KEBAB,         service_name),
        (_T_JAVA_PKG,      new_java_pkg),
        (_T_GRADLE_PKG,    new_gradle_pkg),
        (_T_CLASS_PREFIX,  class_prefix),
        (_T_DISPLAY_NAME,  display_name),
    ]
    if version != _T_VERSION:
        content_replacements.append((f"version={_T_VERSION}", f"version={version}"))

    # Root of the repo is two levels up from this file (.initialise-service-tools/template_tools/cli.py)
    root = Path(__file__).parent.parent.parent.resolve()

    step_update_contents(root, content_replacements, parsed.dry_run)
    step_rename_java_files(root, _T_CLASS_PREFIX, class_prefix, parsed.dry_run)
    step_rename_pkg_dirs(root, _T_JAVA_PKG, new_java_pkg, parsed.dry_run)
    step_rename_subproject_dirs(root, _T_KEBAB, service_name, parsed.dry_run)

    if server_port != _T_SERVER_PORT or mgmt_port != _T_MGMT_PORT:
        section("Updating port numbers")
        step_apply_port_replacements(
            root, service_name,
            _T_SERVER_PORT, server_port,
            _T_MGMT_PORT, mgmt_port,
            parsed.dry_run,
        )

    section("Cleaning up README")
    step_cleanup_readme(root, service_name, parsed.dry_run)

    if use_postgres:
        step_configure_postgres(root, service_name, new_java_pkg, server_port, mgmt_port, parsed.dry_run)

    print()
    print("=" * 65)
    if parsed.dry_run:
        print("  DRY RUN complete — no files were modified.")
        print("  Re-run without --dry-run to apply changes.")
    else:
        print(f"  ✓  Initialisation complete for '{service_name}'!")
        pg_steps = ""
        if use_postgres:
            pg_steps = (
                "\n  7.  .helm/                    Run: helm dependency update .helm/" + core_name +
                "\n                                Set image.registry + image.repository in each values file"
                "\n  8.  TestcontainersConfig      Docker must be running for integration tests to pass"
            )
        print(f"""
  Remaining manual steps
  ──────────────────────────────────────────────────────────
  1.  git diff                  Review every change before committing
  2.  README.md                 Rewrite the TODO section for your service
  3.  open-api-specification.yml  Replace with your own API design
  4.  application.yml           Set sentry.dsn and sentry.environment
  5.  .github/CODEOWNERS        Set your team as code owner
  6.  Remove example domain     Delete Item* classes, schema.sql, data.sql
                                if you don't need them{pg_steps}
  ──────────────────────────────────────────────────────────""")

    if self_delete and not parsed.dry_run:
        try:
            if _FRAGMENTS_DIR.exists():
                shutil.rmtree(_FRAGMENTS_DIR)
                print("  ✓  .initialise-service-fragments deleted.")
        except OSError as exc:
            print(f"  WARNING: Could not delete .initialise-service-fragments — {exc}")

        script = root / "initialise-service.py"
        try:
            if script.exists():
                script.unlink()
                print("  ✓  Script deleted.")
        except OSError as exc:
            print(f"  WARNING: Could not delete script — {exc}")

        tools_dir = Path(__file__).parent.parent
        try:
            shutil.rmtree(tools_dir)
            print("  ✓  .initialise-service-tools deleted.")
        except OSError as exc:
            print(f"  WARNING: Could not delete .initialise-service-tools — {exc}")

    print("=" * 65)
    print()
