# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Bazel build invocation and artifact installation for cmk-dev-deploy.

Invokes ``bazel build``, locates output artifacts, installs them to the OMD
site with correct permissions, and applies post-install fixups.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.subprocess_utils import run_checked
from cmk.dev_deploy.core.timeouts import (
    BAZEL_BUILD,
    BAZEL_CQUERY,
    BAZEL_INFO,
    VERSION_CMD,
)
from cmk.dev_deploy.errors import BazelBuildError
from cmk.dev_deploy.types import (
    BazelTargetSet,
    BuildResult,
    InstallSpec,
    PostInstallAction,
    SiteInfo,
)

CMK_FRONTEND_PROTECT_DIR: str = "cmk-frontend-vue"


def filter_frontend_supervised(
    specs: tuple[InstallSpec, ...],
    frontend_supervised: bool,
) -> tuple[InstallSpec, ...]:
    """Remove frontend-supervised install specs when Vite is active."""
    if not frontend_supervised:
        return specs
    return tuple(s for s in specs if not s.frontend_supervised)


def specs_for_packages(
    packages: frozenset[str],
    all_specs: tuple[InstallSpec, ...] | None = None,
) -> tuple[InstallSpec, ...]:
    """Return InstallSpecs matching any of the given Bazel package paths."""
    if all_specs is None:
        from cmk.dev_deploy.manifest.reader import get_install_specs

        all_specs = get_install_specs()
    return tuple(s for s in all_specs if s.package in packages)


def _get_bazel_info(key: str, repo_root: Path) -> str:
    """Retrieve a value from ``bazel info``."""
    return run_checked(
        ["bazel", "info", key],
        cwd=repo_root,
        timeout=BAZEL_INFO,
        error_cls=BazelBuildError,
        description=f"bazel info {key}",
        recovery="Check Bazel server health with 'bazel info'.",
    ).stdout.strip()


def _get_version(repo_root: Path) -> str:
    """Obtain the Checkmk version string via ``make print-VERSION``."""
    return run_checked(
        ["make", "--quiet", "print-VERSION"],
        cwd=repo_root,
        timeout=VERSION_CMD,
        error_cls=BazelBuildError,
        description="make print-VERSION",
        recovery="Ensure 'make print-VERSION' works in the repo root.",
    ).stdout.strip()


def _build_targets(
    targets: Sequence[str],
    repo_root: Path,
    version: str | None,
    *,
    verbose: bool = False,
) -> None:
    """Invoke ``bazel build`` with all target labels in a single invocation."""
    cmd: list[str] = ["bazel", "build"]
    if version is not None:
        cmd.append(f"--cmk_version={version}")
    cmd.extend(targets)

    if verbose:
        # Pause the spinner so Bazel progress output streams cleanly.
        output.pause_spinner()
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=sys.stderr,
                text=True,
                cwd=str(repo_root),
            )
            try:
                proc.communicate(timeout=BAZEL_BUILD)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise BazelBuildError(
                    f"bazel build timed out after {BAZEL_BUILD}s",
                    recovery="C++ builds can be slow from clean. Retry, or check for build errors.",
                )

            if proc.returncode != 0:
                raise BazelBuildError(
                    "bazel build failed (see output above)",
                    recovery="Check build output above for compilation errors.",
                )
        finally:
            output.resume_spinner()
    else:
        run_checked(
            cmd,
            cwd=repo_root,
            timeout=BAZEL_BUILD,
            error_cls=BazelBuildError,
            description="bazel build",
            recovery="C++ builds can be slow from clean. Retry, or check for build errors.",
        )


def _find_artifact_cquery(
    label: str,
    output_basename: str,
    execution_root: Path,
    repo_root: Path,
) -> Path:
    """Locate a C++ build artifact via ``bazel cquery --output=files``.

    C++ shared libraries have output names that differ from their installation
    names, so cquery is needed to find the actual output path.
    """
    result = run_checked(
        ["bazel", "cquery", "--output=files", label],
        cwd=repo_root,
        timeout=BAZEL_CQUERY,
        error_cls=BazelBuildError,
        description=f"bazel cquery for {label}",
        recovery="Retry -- Bazel server may need warming up.",
    )

    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line.endswith(f"/{output_basename}"):
            return execution_root / line
    raise BazelBuildError(
        f"Artifact '{output_basename}' not found in cquery output for {label}",
        recovery=f"Expected a line ending with '/{output_basename}' in bazel cquery output.",
    )


def _find_artifact_bazel_bin(
    package: str, output_basename: str, bazel_bin: Path
) -> Path:
    """Locate a Rust binary or Vue dist directory in ``bazel-bin``."""
    artifact = bazel_bin / package / output_basename
    if not artifact.exists():
        raise BazelBuildError(
            f"Artifact not found: {artifact}",
            recovery=f"Expected '{output_basename}' at {artifact}. "
            "Ensure the Bazel build completed successfully.",
        )
    return artifact


# ---------------------------------------------------------------------------
# Installation helpers
# ---------------------------------------------------------------------------


def _ensure_writable(dest_dir: Path) -> None:
    """Make all existing files and directories under dest_dir writable.

    Needed on OverlayFS where materialized files have read-only permissions.
    """
    if not dest_dir.is_dir():
        return
    try:
        dest_dir.chmod(dest_dir.stat().st_mode | 0o200)
    except OSError:
        pass
    for entry in dest_dir.rglob("*"):
        try:
            entry.chmod(entry.stat().st_mode | 0o200)
        except OSError:
            pass


def _files_identical(a: Path, b: Path) -> bool:
    """Return True if two files have identical content (compared by mmap)."""
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
    except OSError:
        return False
    # Small files: direct byte comparison
    return a.read_bytes() == b.read_bytes()


def _install_binary(source: Path, dest: Path, mode: int) -> bool:
    """Install a binary artifact, skipping if content is unchanged.

    Unlinks before copying to create a fresh inode -- avoids ETXTBSY on
    running executables and mmap corruption on shared libraries.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and _files_identical(source, dest):
        output.verbose(f"  {dest.name}: unchanged, skipping copy")
        return False
    # Remove existing file so the copy creates a fresh inode.
    # Missing file (first deploy) is fine.
    dest.unlink(missing_ok=True)
    shutil.copy2(source, dest)
    os.chmod(dest, mode)
    return True


def _has_capability(path: Path, cap: str) -> bool:
    """Check whether a file already has the given capability set."""
    result = subprocess.run(
        ["getcap", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    # getcap output looks like: "/path/to/binary cap_net_raw=ep"
    return result.returncode == 0 and cap.rstrip("+ep") in result.stdout


def _run_setcap(installed: Path, cap: str) -> bool:
    """Apply Linux file capabilities after install if not already set.

    Must run after every fresh install since ``shutil.copy2`` does not
    preserve extended attributes.
    """
    from cmk.dev_deploy.site.privilege import try_setcap

    if _has_capability(installed, cap):
        output.verbose(f"  {installed.name}: {cap} already set, skipping")
        return False

    return try_setcap(installed, cap)


def _copy_directory(
    source_dir: Path,
    dest_dir: Path,
    delete: bool,
    protect_subdir: str | None,
) -> None:
    """Copy a built directory (Vue/frontend dist) to the site."""
    if delete and protect_subdir:
        # Preserve protected subdirectory during clean
        protected = dest_dir / protect_subdir
        protected_tmp = None
        if protected.is_dir():
            protected_tmp = protected.with_suffix(".protected_tmp")
            protected.rename(protected_tmp)
        if dest_dir.is_dir():
            shutil.rmtree(dest_dir)
        shutil.copytree(source_dir, dest_dir)
        if protected_tmp and protected_tmp.is_dir():
            restored = dest_dir / protect_subdir
            if restored.exists():
                shutil.rmtree(restored)
            protected_tmp.rename(restored)
    elif delete:
        if dest_dir.is_dir():
            shutil.rmtree(dest_dir)
        shutil.copytree(source_dir, dest_dir)
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)
        # Ensure existing files and directories are writable before
        # copying.  On OverlayFS, the upper layer has materialized
        # content with read-only permissions from the version dir.
        _ensure_writable(dest_dir)
        shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)

    # Apply u+w so files and directories are editable by deploy user
    for entry in dest_dir.rglob("*"):
        try:
            entry.chmod(entry.stat().st_mode | 0o200)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_and_install(
    targets: BazelTargetSet,
    site: SiteInfo,
    repo_root: Path,
    *,
    verbose: bool = False,
    frontend_supervised: bool = False,
) -> BuildResult:
    """Build Bazel targets and install artifacts to the OMD site.

    Single public entry point for compiled-asset deployment: collects specs,
    filters by edition, builds once, locates artifacts, installs with correct
    permissions, and applies post-install fixups (setcap, etc.).
    """
    start = time.monotonic()

    # 1. Collect matching install specs for the resolved packages
    packages = frozenset(t.package for t in targets.targets)
    all_specs = specs_for_packages(packages)

    # 1b. Filter frontend-supervised specs when Vite is active
    if frontend_supervised:
        filtered = filter_frontend_supervised(all_specs, True)
        if len(filtered) < len(all_specs):
            from cmk.dev_deploy.core import output as _output

            _output.print_frontend_skip("cmk-frontend-vue")
        all_specs = filtered

    # 2-3. Filter by edition, source directory existence, and faked artifacts
    active_specs: list[InstallSpec] = []
    skipped_edition = 0
    for spec in all_specs:
        if spec.needs_faked_artifacts:
            # Cross-compiled artifacts (e.g. mk-oracle) are not available
            # in local dev checkouts — skip rather than deploy placeholders.
            skipped_edition += 1
            continue
        if not site.edition.matches(spec.edition_constraint):
            skipped_edition += 1
            continue
        # Non-free packages may be absent in community checkouts
        if not (repo_root / spec.package).is_dir():
            skipped_edition += 1
            continue
        active_specs.append(spec)

    if not active_specs:
        return BuildResult(
            targets_built=0,
            artifacts_installed=0,
            elapsed=time.monotonic() - start,
            skipped_edition=skipped_edition,
        )

    # 4. Determine version flag and collect build labels
    version: str | None = None
    if any(s.needs_version_flag for s in active_specs):
        version = _get_version(repo_root)

    # Deduplicate build labels (multiple specs can share a package_target)
    seen_labels: set[str] = set()
    labels: list[str] = []
    for spec in active_specs:
        if spec.package_target not in seen_labels:
            seen_labels.add(spec.package_target)
            labels.append(spec.package_target)

    # 5. Single bazel build invocation for all targets
    _build_targets(labels, repo_root, version, verbose=verbose)

    # 6. Get info paths for artifact discovery
    execution_root = Path(_get_bazel_info("execution_root", repo_root))
    bazel_bin = Path(_get_bazel_info("bazel-bin", repo_root))

    # 7. Locate and install each artifact
    installed_count = 0
    for spec in active_specs:
        if not spec.install_dest.strip():
            output.error(
                f"Install spec '{spec.package}' has empty site_dest -- skipping to avoid "
                f"deploying into the site root (source: {spec.package})"
            )
            continue

        # Locate artifact: try bazel-bin first (Rust, Vue/frontend),
        # fall back to cquery (C++ shared libs with non-trivial output paths)
        try:
            source = _find_artifact_bazel_bin(
                spec.package, spec.output_basename, bazel_bin
            )
        except BazelBuildError:
            source = _find_artifact_cquery(
                spec.package_target,
                spec.output_basename,
                execution_root,
                repo_root,
            )

        installed_path = site.root / spec.install_dest

        # Install: copytree for directories, copy+chmod for binaries
        if spec.use_copytree:
            # cmk-frontend uses delete with protect for cmk-frontend-vue
            is_legacy_frontend = spec.install_dest == "share/check_mk/web/htdocs"
            _copy_directory(
                source_dir=source,
                dest_dir=installed_path,
                delete=is_legacy_frontend,
                protect_subdir=CMK_FRONTEND_PROTECT_DIR if is_legacy_frontend else None,
            )
            changed = True
        else:
            changed = _install_binary(source, installed_path, spec.mode)

        # Apply post-install actions (only when binary was actually replaced;
        # unchanged binaries keep their existing capabilities)
        if changed:
            for action in spec.post_install:
                if action == PostInstallAction.SETCAP_NET_RAW:
                    _run_setcap(installed_path, "cap_net_raw+ep")

        installed_count += 1

    elapsed = time.monotonic() - start
    return BuildResult(
        targets_built=len(labels),
        artifacts_installed=installed_count,
        elapsed=elapsed,
        skipped_edition=skipped_edition,
    )
