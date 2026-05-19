"""
Shared utility functions: prompting, derivation, validation, file I/O.
"""
import os
import re
from pathlib import Path

from .constants import (
    _T_KEBAB, SKIP_DIRS, SKIP_FILES, SKIP_EXTS, JAVA_KEYWORDS,
)


# ── Name derivation ────────────────────────────────────────────────────────────

def strip_laa(name: str) -> str:
    """laa-my-service -> my-service"""
    return re.sub(r"^laa-", "", name)


def to_pascal(kebab: str) -> str:
    """my-service -> MyService"""
    return "".join(w.capitalize() for w in kebab.split("-"))


def to_pkg(kebab: str) -> str:
    """my-service -> my.service"""
    return re.sub(r"[^a-z0-9.]", ".", kebab.lower())


def to_display(kebab: str) -> str:
    """my-service -> LAA My Service"""
    return "LAA " + " ".join(w.capitalize() for w in kebab.split("-"))


# ── Prompting ──────────────────────────────────────────────────────────────────

def prompt(question: str, default: str = "", required: bool = False) -> str:
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


def prompt_yn(question: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        answer = input(f"  {question} [{hint}]: ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in ("y", "yes")


# ── Validation ─────────────────────────────────────────────────────────────────

def validate(service_name: str, pkg_suffix: str, class_prefix: str) -> list[str]:
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
            errors.append(f"Package segment '{seg}' is not a valid Java identifier.")
        elif seg in JAVA_KEYWORDS:
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


# ── File helpers ───────────────────────────────────────────────────────────────

def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    if path.name in SKIP_FILES:
        return True
    if path.suffix in SKIP_EXTS:
        return True
    return False


def replace_in_file(
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


def remove_empty_parents(path: Path, stop_at: Path) -> None:
    current = path
    while current != stop_at:
        try:
            current.rmdir()
            current = current.parent
        except OSError:
            break


def targeted_replace(path: Path, pairs: list[tuple[str, str]], dry_run: bool) -> None:
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


def resolve_service_dir(root: Path, service_name: str) -> Path | None:
    """Locate the service module directory that contains a build.gradle."""
    candidates = [
        root / f"{service_name}-service",
        root / f"{strip_laa(service_name)}-service",
        root / f"{_T_KEBAB}-service",
    ]
    for c in candidates:
        if (c / "build.gradle").exists():
            return c

    service_dirs = sorted(
        p for p in root.glob("*-service")
        if p.is_dir() and (p / "build.gradle").exists()
    )
    if len(service_dirs) == 1:
        return service_dirs[0]
    if len(service_dirs) > 1:
        likely = [p for p in service_dirs if service_name in p.name or strip_laa(service_name) in p.name]
        if len(likely) == 1:
            return likely[0]
    return None


def section(title: str) -> None:
    print(f"\n{chr(8212) * 65}")
    print(f"  {title}")
    print(chr(8212) * 65)
