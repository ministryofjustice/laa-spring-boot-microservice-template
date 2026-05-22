"""
PostgreSQL configuration step — patches build.gradle, application.yml,
docker-compose.yml, writes Flyway migrations, and TestcontainersConfig.java.
"""
import os
import re
from pathlib import Path

from .constants import (
    _FRAGMENTS_DIR, _T_TESTCONTAINERS_BOM_VERSION,
)
from .helpers import resolve_service_dir, section


def step_configure_postgres(
    root: Path,
    service_name: str,
    new_java_pkg: str,
    server_port: str,
    mgmt_port: str,
    dry_run: bool,
) -> None:
    """Switch service from H2 to PostgreSQL (RDS-ready)."""
    section("Step 5 / 5  —  Configuring PostgreSQL (RDS-ready)")

    pg_dir = _FRAGMENTS_DIR / "postgres"
    core = re.sub(r"^laa-", "", service_name)
    tokens = {
        "%%SERVICE_KEBAB%%": core,
        "%%JAVA_PKG%%":      new_java_pkg,
        "%%SERVER_PORT%%":   server_port,
        "%%MGMT_PORT%%":     mgmt_port,
    }

    def fill(text: str) -> str:
        for tok, val in tokens.items():
            text = text.replace(tok, val)
        return text

    def write(dest: Path, text: str) -> None:
        rel = dest.relative_to(root)
        if dest.exists():
            try:
                existing = dest.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                existing = None
            if existing == text:
                print(f"    Unchanged    : {rel}")
                return
            print(f"    Skipped      : {rel} (already exists — review manually)")
            return
        if dry_run:
            print(f"    Would write  : {rel}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            print(f"    Written      : {rel}")

    def fragment(name: str) -> str:
        return fill((pg_dir / name).read_text(encoding="utf-8"))

    # ── Locate service module ──────────────────────────────────────────────────
    service_dir = resolve_service_dir(root, service_name)
    if service_dir is None:
        discovered = sorted(p.name for p in root.glob("*-service") if p.is_dir())
        print("    WARNING: could not resolve service module directory.")
        if discovered:
            print(f"             Found service-like dirs: {', '.join(discovered)}")
        print("             Skipping PostgreSQL file patches for service module.")
        return

    print(f"    Using service module: {service_dir.relative_to(root)}")

    # ── 1. build.gradle ───────────────────────────────────────────────────────
    build_gradle = service_dir / "build.gradle"
    if build_gradle.exists():
        original = build_gradle.read_text(encoding="utf-8")
        updated = original
        changed = False

        h2_anchor = "    runtimeOnly 'com.h2database:h2'"
        tc_anchor = "    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'"
        runtime_block = fragment("build-gradle-additions.txt").rstrip()
        test_block    = fragment("build-gradle-test-additions.txt").rstrip()

        if h2_anchor in updated:
            updated = updated.replace(h2_anchor, runtime_block)
            changed = True
        elif any(x in updated for x in ("org.postgresql:postgresql", "spring-boot-starter-flyway")):
            print("    build.gradle : postgres/flyway deps already present — skipping")
        else:
            print(
                "    WARNING: build.gradle — H2 anchor not found\n"
                f"             Expected:  {h2_anchor}\n"
                "             Please add postgres/flyway deps manually."
            )

        if test_block in updated:
            print("    build.gradle : testcontainers deps already present — skipping")
        elif any(x in updated for x in ("spring-boot-testcontainers", "testcontainers:postgresql")):
            print("    build.gradle : testcontainers deps already present — skipping")
        elif tc_anchor in updated:
            updated = updated.replace(tc_anchor, test_block + "\n\n" + tc_anchor)
            changed = True
        else:
            print(
                "    WARNING: build.gradle — testRuntimeOnly anchor not found\n"
                f"             Expected:  {tc_anchor}\n"
                "             Please add testcontainers deps manually."
            )

        has_tc_modules = any(x in updated for x in ("testcontainers:junit-jupiter", "testcontainers:postgresql"))
        has_tc_bom     = "testcontainers:testcontainers-bom" in updated
        if has_tc_modules and not has_tc_bom:
            bom_line   = f"    testImplementation platform('org.testcontainers:testcontainers-bom:{_T_TESTCONTAINERS_BOM_VERSION}')\n"
            bom_anchor = "    testImplementation 'org.springframework.boot:spring-boot-testcontainers'"
            if bom_anchor in updated:
                updated = updated.replace(bom_anchor, bom_line + bom_anchor, 1)
                changed = True
                print("    build.gradle : added testcontainers BOM")
            else:
                print("    WARNING: build.gradle — could not insert testcontainers BOM (anchor not found)")

        if changed:
            if not dry_run:
                build_gradle.write_text(updated, encoding="utf-8")
            print(f"    Updated      : {build_gradle.relative_to(root)}")
    else:
        print(f"    WARNING: build.gradle not found at {build_gradle.relative_to(root)}")

    # ── 2. application.yml ────────────────────────────────────────────────────
    app_yml  = service_dir / "src" / "main" / "resources" / "application.yml"
    if app_yml.exists():
        original = app_yml.read_text(encoding="utf-8")
        ds_fragment = fragment("application-datasource.yml").rstrip()
        if "jdbc:postgresql://" in original:
            print("    application.yml: postgres datasource already configured — skipping")
        else:
            updated = re.sub(
                r" {2}# example database\n {2}datasource:.*?ddl-auto: none",
                ds_fragment,
                original,
                flags=re.DOTALL,
            )
            if updated != original:
                if not dry_run:
                    app_yml.write_text(updated, encoding="utf-8")
                print(f"    Updated      : {app_yml.relative_to(root)}")
            else:
                print(
                    "    WARNING: application.yml — could not find H2 datasource block\n"
                    "             Expected anchor: '  # example database'\n"
                    "             Please replace the datasource/jpa block manually."
                )
    else:
        print(f"    WARNING: application.yml not found at {app_yml.relative_to(root)}")

    # ── 3. Flyway migrations ──────────────────────────────────────────────────
    resources_dir = service_dir / "src" / "main" / "resources"
    migration_dir = resources_dir / "db" / "migration"
    write(migration_dir / "V1__create_items_table.sql", fragment("V1__create_items_table.sql"))
    write(migration_dir / "V2__seed_items.sql",         fragment("V2__seed_items.sql"))

    for old_file in (resources_dir / "schema.sql", resources_dir / "data.sql"):
        if old_file.exists():
            if dry_run:
                print(f"    Would delete : {old_file.relative_to(root)}")
            else:
                old_file.unlink()
                print(f"    Deleted      : {old_file.relative_to(root)}")

    # ── 4. docker-compose.yml ─────────────────────────────────────────────────
    compose_file = root / "docker-compose.yml"
    if compose_file.exists():
        original      = compose_file.read_text(encoding="utf-8")
        pg_service    = fragment("docker-compose-postgres.yml")
        app_env_vars  = fragment("docker-compose-app-env.yml")
        updated       = original

        if re.search(r"(?m)^  postgres:\n", updated):
            print("    docker-compose.yml: postgres service already configured — skipping")
        elif "services:\n" in updated:
            updated = updated.replace("services:\n", "services:\n" + pg_service + "\n", 1)

        if "DB_HOST" in updated and "depends_on:" in updated:
            print("    docker-compose.yml: app DB env vars already configured — skipping")
        else:
            anchor = "    environment:\n      - SERVER_PORT="
            if anchor in updated:
                updated = updated.replace(
                    anchor,
                    "    depends_on:\n      postgres:\n        condition: service_healthy\n"
                    "    environment:\n" + app_env_vars + "      - SERVER_PORT=",
                    1,
                )

        if updated != original:
            if not dry_run:
                compose_file.write_text(updated, encoding="utf-8")
            print(f"    Updated      : {compose_file.relative_to(root)}")
        else:
            print("    WARNING: could not patch docker-compose.yml — check manually")

    # ── 5. TestcontainersConfig.java ──────────────────────────────────────────
    pkg_path = new_java_pkg.replace(".", os.sep)
    tc_dest = (
        service_dir / "src" / "integrationTest" / "java" / pkg_path / "TestcontainersConfig.java"
    )
    write(tc_dest, fragment("TestcontainersConfig.java"))

    # ── 6. Patch ItemControllerIntegrationTest ────────────────────────────────
    it_file = (
        service_dir / "src" / "integrationTest" / "java" / pkg_path
        / "controller" / "ItemControllerIntegrationTest.java"
    )
    if it_file.exists():
        original     = it_file.read_text(encoding="utf-8")
        import_line  = f"import {new_java_pkg}.TestcontainersConfig;\n"
        spring_imp   = "import org.springframework.context.annotation.Import;\n"
        updated      = original
        if spring_imp not in updated and "@SpringBootTest(" in updated:
            updated = updated.replace("@SpringBootTest(", spring_imp + "\n@SpringBootTest(", 1)
        if import_line not in updated and "@SpringBootTest(" in updated:
            updated = updated.replace("@SpringBootTest(", import_line + "\n@SpringBootTest(", 1)
        if "@Import(TestcontainersConfig.class)" not in updated and "@SpringBootTest(" in updated:
            updated = updated.replace("@SpringBootTest(", "@Import(TestcontainersConfig.class)\n@SpringBootTest(", 1)
        if updated != original:
            if not dry_run:
                it_file.write_text(updated, encoding="utf-8")
            print(f"    Updated      : {it_file.relative_to(root)}")

    # ── 7. README postgres references ─────────────────────────────────────────
    _update_readme_for_postgres(root, dry_run)

    print("\n    PostgreSQL configuration complete.")


def _update_readme_for_postgres(root: Path, dry_run: bool) -> None:
    readme = root / "README.md"
    if not readme.exists():
        return
    try:
        content = readme.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return
    updated = content
    updated = updated.replace(
        "with CRUD operations interfacing a JPA repository with an in-memory database.",
        "with CRUD operations interfacing a JPA repository with a PostgreSQL database.",
    )
    updated = re.sub(
        r"- \[H2\]\(https://www\.h2database\.com/html/main\.html\) - .*",
        "- [PostgreSQL](https://www.postgresql.org/) - used to provide a local/example database.",
        updated,
    )
    if updated != content:
        if not dry_run:
            readme.write_text(updated, encoding="utf-8")
        print("    Updated      : README.md (replaced H2 references with PostgreSQL)")
