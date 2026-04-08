# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Config/data deployment engine for non-compiled assets.

Data-driven deployer for agents/, notifications/, locale/, doc/, etc.
using copy_dir, install_files, or locale_compile methods.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.timeouts import MSGFMT
from cmk.dev_deploy.errors import ConfigDeployError
from cmk.dev_deploy.manifest.reader import get_config_specs
from cmk.dev_deploy.types import (
    ChangeCategory,
    ChangeSet,
    ConfigDeployResult,
    ConfigDeploySpec,
    ConfigFileEntry,
    DeployMethod,
    SiteInfo,
)


def specs_for_changed_files(
    changed_files: tuple[str, ...],
    all_specs: tuple[ConfigDeploySpec, ...] | None = None,
) -> tuple[ConfigDeploySpec, ...]:
    """Return only the specs whose source_prefix matches any changed file.

    Multiple specs can match the same file (e.g. ``agents/plugins/`` and
    ``agents/``). Uses longest-prefix-first matching internally but
    preserves the original tuple ordering in the result.
    """
    if all_specs is None:
        all_specs = get_config_specs()

    # Sort by descending source_prefix length for longest-prefix-first matching
    sorted_specs = sorted(all_specs, key=lambda s: len(s.source_prefix), reverse=True)

    # Find all matching specs
    matched: set[str] = set()
    for spec in sorted_specs:
        if any(f.startswith(spec.source_prefix) for f in changed_files):
            matched.add(spec.source_prefix)

    # Return in original tuple order
    return tuple(s for s in all_specs if s.source_prefix in matched)


# ---------------------------------------------------------------------------
# Private deployment methods
# ---------------------------------------------------------------------------


def _resolve_mode(entry_mode: str, spec_mode: int | None, file_chmod: str | None) -> int | None:
    """Resolve the effective file mode from entry, spec, and chmod override."""
    mode = int(entry_mode, 8) if entry_mode else spec_mode
    if file_chmod is not None:
        mode = int(file_chmod, 8)
    return mode


def _resolve_src(entry: ConfigFileEntry, repo_root: Path) -> Path:
    """Resolve the source path for a config file entry.

    Generated files (``file_from_flag``, etc.) live under ``bazel-bin/``
    rather than directly in the repo tree.
    """
    if entry.generated:
        return repo_root / "bazel-bin" / entry.src
    return repo_root / entry.src


def _copy_dir(source: Path, dest: Path, spec: ConfigDeploySpec, repo_root: Path) -> None:
    """Copy a config/data directory to the site using the Bazel-derived file list.

    Uses individual file copy when ``spec.files`` is non-empty (with optional
    delete_extra cleanup), otherwise falls back to ``shutil.copytree()``.
    """
    dest.mkdir(parents=True, exist_ok=True)

    if spec.files:
        # Copy using the Bazel-derived file list
        prefix = spec.source_prefix.rstrip("/") + "/"
        expected_files: set[str] = set()

        for entry in spec.files:
            src_path = _resolve_src(entry, repo_root)
            if not src_path.is_file():
                continue

            if entry.src.startswith(prefix):
                rel = entry.src[len(prefix) :]
            elif entry.src == spec.source_prefix.rstrip("/"):
                rel = "."
            else:
                rel = entry.src

            dst = dest / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst)

            # Apply file mode
            mode = _resolve_mode(entry.mode, spec.mode, spec.file_chmod)
            if mode:
                os.chmod(dst, mode)

            expected_files.add(rel)

        # Also copy files matching include patterns (dev convenience)
        for pattern in spec.includes:
            for match in source.glob(pattern):
                if match.is_file():
                    rel = str(match.relative_to(source))
                    dst = dest / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(match, dst)
                    mode = _resolve_mode("", spec.mode, spec.file_chmod)
                    if mode:
                        os.chmod(dst, mode)
                    expected_files.add(rel)

        # Delete extra files at dest not present in source
        if spec.delete_extra:
            for existing in dest.rglob("*"):
                if existing.is_file():
                    rel = str(existing.relative_to(dest))
                    if rel not in expected_files:
                        existing.unlink()
    else:
        # Fallback: copy the full directory
        if dest.is_dir():
            shutil.rmtree(dest)
        shutil.copytree(
            source,
            dest,
            dirs_exist_ok=True,
        )

        # Apply chmod if specified
        if spec.file_chmod is not None:
            chmod_val = int(spec.file_chmod, 8)
            for f in dest.rglob("*"):
                if f.is_file():
                    os.chmod(f, chmod_val)


def _install_files(source: Path, dest: Path, spec: ConfigDeploySpec, repo_root: Path) -> int:
    """Install individual files from source to dest with explicit permissions."""
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    if spec.files:
        for entry in spec.files:
            src_path = _resolve_src(entry, repo_root)
            if not src_path.is_file():
                continue
            dest_file = dest / src_path.name
            shutil.copy2(src_path, dest_file)
            mode = _resolve_mode(entry.mode, spec.mode, spec.file_chmod)
            if mode:
                os.chmod(dest_file, mode)
            count += 1
    else:
        for src_entry in sorted(source.iterdir()):
            if src_entry.is_dir():
                continue
            assert spec.mode is not None
            shutil.copy2(src_entry, dest / src_entry.name)
            os.chmod(dest / src_entry.name, spec.mode)
            count += 1

    return count


def _compile_and_deploy_locale(source: Path, dest: Path, spec: ConfigDeploySpec) -> tuple[int, int]:
    """Compile .po -> .mo via msgfmt, then install per-language directories."""
    po_compiled = 0

    # Pass 1: compile all .po -> .mo
    for po_file in source.rglob("*.po"):
        mo_file = po_file.with_suffix(".mo")
        try:
            result = subprocess.run(
                ["msgfmt", "-o", str(mo_file), str(po_file)],
                capture_output=True,
                text=True,
                check=False,
                timeout=MSGFMT,
            )
        except FileNotFoundError:
            raise ConfigDeployError(
                "msgfmt not found -- cannot compile locale files",
                recovery="Install gettext: apt install gettext",
            )
        except subprocess.TimeoutExpired:
            raise ConfigDeployError(
                f"msgfmt timed out after {MSGFMT}s for {po_file}",
                recovery="Install gettext: apt install gettext",
            )

        if result.returncode != 0:
            raise ConfigDeployError(
                f"msgfmt failed for {po_file}: {result.stderr.strip()}",
                recovery="Install gettext: apt install gettext",
            )
        po_compiled += 1

    # Pass 2: install per-language directories
    files_installed = 0

    if spec.files:
        # Extract language codes from the Bazel-derived file list
        prefix = spec.source_prefix.rstrip("/") + "/"
        languages: set[str] = set()
        for entry in spec.files:
            if entry.src.startswith(prefix):
                relative = entry.src[len(prefix) :]
                # First path component is the language code (e.g. "de/LC_MESSAGES/...")
                lang = relative.split("/", 1)[0]
                if lang:
                    languages.add(lang)
        lang_dirs = sorted(languages)
    else:
        # Fallback: scan directory for language-pattern entries
        lang_dirs = []
        for dir_entry in sorted(source.iterdir()):
            if not dir_entry.is_dir():
                continue
            name = dir_entry.name
            if len(name) == 2 or (len(name) == 5 and name[2] == "_"):
                lang_dirs.append(name)

    for name in lang_dirs:
        lang_dir = source / name
        if not lang_dir.is_dir():
            continue

        lc_dest = dest / name / "LC_MESSAGES"
        lc_dest.mkdir(parents=True, exist_ok=True)

        # Install alias file if present
        alias_file = lang_dir / "alias"
        if alias_file.exists():
            shutil.copy2(alias_file, dest / name / "alias")
            os.chmod(dest / name / "alias", 0o644)

        # Install compiled multisite.mo if present
        mo_file = lang_dir / "LC_MESSAGES" / "multisite.mo"
        if mo_file.exists():
            shutil.copy2(mo_file, lc_dest / "multisite.mo")
            os.chmod(lc_dest / "multisite.mo", 0o644)
            files_installed += 1

    return files_installed, po_compiled


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def deploy_config(changes: ChangeSet | None, repo_root: Path, site: SiteInfo) -> ConfigDeployResult:
    """Deploy config/data files to the OMD site.

    Deploys all specs when ``changes`` is None, otherwise only specs
    matching the changed CONFIG and DATA files.
    """
    start = time.monotonic()

    # Determine active specs
    if changes is None:
        active_specs = get_config_specs()
    else:
        config_files = changes.categories.get(ChangeCategory.CONFIG, ())
        data_files = changes.categories.get(ChangeCategory.DATA, ())
        combined = config_files + data_files
        if not combined:
            elapsed = time.monotonic() - start
            return ConfigDeployResult(
                specs_deployed=0,
                files_installed=0,
                elapsed=elapsed,
                locale_compiled=0,
            )
        active_specs = specs_for_changed_files(combined)

    if not active_specs:
        elapsed = time.monotonic() - start
        return ConfigDeployResult(
            specs_deployed=0,
            files_installed=0,
            elapsed=elapsed,
            locale_compiled=0,
        )

    # Deploy each active spec
    specs_deployed = 0
    files_installed = 0
    locale_compiled = 0

    for spec in active_specs:
        source_dir = repo_root / spec.source_prefix.rstrip("/")

        if not spec.site_dest.strip():
            output.error(
                f"Config spec has empty site_dest -- skipping to avoid "
                f"deploying into the site root (source: {spec.source_prefix})"
            )
            continue

        dest_dir = site.root / spec.site_dest.rstrip("/")

        if not source_dir.is_dir():
            output.warn(f"Source directory not found, skipping: {source_dir}")
            continue

        if spec.method == DeployMethod.COPY_DIR:
            _copy_dir(source_dir, dest_dir, spec, repo_root)
        elif spec.method == DeployMethod.INSTALL_FILES:
            files_installed += _install_files(source_dir, dest_dir, spec, repo_root)
        elif spec.method == DeployMethod.LOCALE_COMPILE:
            installed, compiled = _compile_and_deploy_locale(source_dir, dest_dir, spec)
            files_installed += installed
            locale_compiled += compiled

        specs_deployed += 1

    elapsed = time.monotonic() - start
    return ConfigDeployResult(
        specs_deployed=specs_deployed,
        files_installed=files_installed,
        elapsed=elapsed,
        locale_compiled=locale_compiled,
    )
