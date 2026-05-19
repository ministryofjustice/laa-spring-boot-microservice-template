"""
Core initialisation steps: content replacement, file/dir renaming, port
updates, and README cleanup.
"""
import os
import re
import shutil
from pathlib import Path

from .constants import _T_KEBAB, _T_SERVER_PORT, _T_MGMT_PORT
from .helpers import (
    should_skip, replace_in_file, remove_empty_parents,
    targeted_replace, section,
)


def step_update_contents(
    root: Path,
    replacements: list[tuple[str, str]],
    dry_run: bool,
) -> None:
    section("Step 1 / 4  —  Updating file contents")
    changed = 0
    for dirpath, dirnames, filenames in os.walk(root):
        from .constants import SKIP_DIRS
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if should_skip(fpath):
                continue
            if replace_in_file(fpath, replacements, dry_run):
                print(f"    Updated  : {fpath.relative_to(root)}")
                changed += 1
    print(f"\n    {changed} file(s) updated.")


def step_rename_java_files(
    root: Path,
    old_prefix: str,
    new_prefix: str,
    dry_run: bool,
) -> None:
    section("Step 2 / 4  —  Renaming Java source files")
    targets = [
        (f"{old_prefix}Application.java",     f"{new_prefix}Application.java"),
        (f"{old_prefix}ApplicationTests.java", f"{new_prefix}ApplicationTests.java"),
    ]
    found = False
    for old_name, new_name in targets:
        for match in root.rglob(old_name):
            if should_skip(match):
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
) -> None:
    section("Step 3 / 4  —  Renaming Java package directories")
    old_rel = Path(old_java_pkg.replace(".", os.sep))
    new_rel = Path(new_java_pkg.replace(".", os.sep))

    found = False
    for java_dir in root.rglob("java"):
        if should_skip(java_dir) or not java_dir.is_dir():
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
            remove_empty_parents(old_pkg_dir.parent, stop_at=java_dir)
        found = True
    if not found:
        print("    Nothing to rename.")


def step_rename_subproject_dirs(
    root: Path,
    old_kebab: str,
    new_kebab: str,
    dry_run: bool,
) -> None:
    section("Step 4 / 4  —  Renaming subproject directories")
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


def step_apply_port_replacements(
    root: Path,
    service_name: str,
    old_server: str,
    new_server: str,
    old_mgmt: str,
    new_mgmt: str,
    dry_run: bool,
) -> None:
    if old_server == new_server and old_mgmt == new_mgmt:
        return

    app_yml = root / f"{service_name}-service" / "src" / "main" / "resources" / "application.yml"
    if not app_yml.exists():
        app_yml = root / f"{_T_KEBAB}-service" / "src" / "main" / "resources" / "application.yml"

    targeted_replace(app_yml, [
        (f"port: {old_server}", f"port: {new_server}"),
        (f"port: {old_mgmt}",   f"port: {new_mgmt}"),
    ], dry_run)
    targeted_replace(root / "Dockerfile", [
        (f"EXPOSE {old_server} {old_mgmt}", f"EXPOSE {new_server} {new_mgmt}"),
    ], dry_run)
    targeted_replace(root / "docker-compose.yml", [
        (f'"{old_server}:{old_server}"', f'"{new_server}:{new_server}"'),
        (f'"{old_mgmt}:{old_mgmt}"',     f'"{new_mgmt}:{new_mgmt}"'),
    ], dry_run)
    targeted_replace(root / "README.md", [
        (f"localhost:{old_server}", f"localhost:{new_server}"),
    ], dry_run)


def step_cleanup_readme(root: Path, service_name: str, dry_run: bool) -> None:
    readme = root / "README.md"
    if not readme.exists():
        return
    try:
        content = readme.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return

    updated = content
    updated = re.sub(
        r"### ⚠️ WORK IN PROGRESS ⚠️\n.*?\n\n",
        "",
        updated,
        flags=re.DOTALL,
    )
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
