# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Direct wheel deployment engine: copy + .dist-info + compileall.

Copies Python source directly to site-packages (no Bazel, no pip) for most
packages. Generated-source packages (cmk-shared-typing, cmc-protocols) use
``bazel build :wheel`` + zipfile extraction instead.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import shutil
import subprocess
import sys
import time
import zipfile
from collections.abc import Iterable
from concurrent.futures import as_completed, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.subprocess_utils import run_checked
from cmk.dev_deploy.core.timeouts import (
    BAZEL_CQUERY_QUICK,
    BAZEL_INFO,
    BAZEL_WHEEL_BUILD,
)
from cmk.dev_deploy.deployers._distribution_info import (
    build_package_info_from_spec as _build_package_info_from_spec,
)
from cmk.dev_deploy.deployers._distribution_info import (
    DistributionInfo as _DistributionInfo,
)
from cmk.dev_deploy.deployers._distribution_info import (
    PackageInfo as _PackageInfo,
)
from cmk.dev_deploy.deployers._site_python import get_site_packages
from cmk.dev_deploy.errors import WheelDeployError
from cmk.dev_deploy.manifest.reader import get_wheel_specs
from cmk.dev_deploy.site.edition_filter import filter_edition_files, filter_editions
from cmk.dev_deploy.state.deploy_state import compute_dirty_hashes, get_head_commit
from cmk.dev_deploy.state.path_skip import check_skip
from cmk.dev_deploy.types import (
    ChangeSet,
    SiteInfo,
    SkipResult,
    WheelDeployMode,
    WheelDeployResult,
    WheelDeploySpec,
)

# The main ``cmk`` wheel (``//cmk:whl``) is special: its files live at
# ``lib/python3/cmk/`` in the OMD site tree, NOT in ``site-packages/``.
# Sub-packages (cmk-ccc, cmk-trace, …) deploy to ``site-packages/``
# normally because their ``source_subdirs`` already contain the full
# namespace path (e.g. ``cmk/ccc/``).  The monolithic cmk wheel's
# subdirs are relative to the ``cmk/`` package dir (e.g. ``gui/wsgi/``)
# so the deployer must map them to ``lib/python3/cmk/gui/wsgi/``.
_CMK_WHEEL_PACKAGE = "cmk"
_CMK_WHEEL_SITE_SUBDIR = Path("lib") / "python3"


def _get_deploy_roots(
    spec: WheelDeploySpec, site: SiteInfo, site_packages: Path
) -> tuple[Path, Path]:
    """Return ``(file_root, dist_info_root)`` for a wheel spec."""
    if spec.package == _CMK_WHEEL_PACKAGE:
        cmk_root = site.root / _CMK_WHEEL_SITE_SUBDIR
        return (cmk_root / _CMK_WHEEL_PACKAGE, cmk_root)
    return (site_packages, site_packages)


if TYPE_CHECKING:
    from cmk.dev_deploy.state.deploy_state import DeployerState, DeployState

_DIST_INFO_VERSION: str = "1.0.0"
TARGETED_THRESHOLD: int = 15


@dataclass(frozen=True)
class StepTiming:
    """Timing data for a single deployment step."""

    name: str
    elapsed: float
    file_count: int = 0


@dataclass
class _StepRecorder:
    """Lap-timer that collects :class:`StepTiming` entries."""

    steps: list[StepTiming] = field(default_factory=list)
    _start: float = 0.0

    def begin(self) -> None:
        self._start = time.monotonic()

    def record(self, name: str, file_count: int = 0) -> None:
        now = time.monotonic()
        self.steps.append(StepTiming(name=name, elapsed=now - self._start, file_count=file_count))
        self._start = now

    def freeze(self) -> tuple[StepTiming, ...]:
        return tuple(self.steps)


# ---------------------------------------------------------------------------
# Targeted deploy helpers (for edition_filter packages like cmk/)
# ---------------------------------------------------------------------------


def _can_use_targeted(
    modified_py_files: list[str],
    fallback_reason: str,
    dest_base: Path,
    prefix: str,
) -> tuple[bool, str]:
    """Check whether the targeted deploy path is eligible for a package."""
    if fallback_reason:
        return (False, fallback_reason)
    if not modified_py_files:
        return (False, "no Python file modifications")
    if len(modified_py_files) > TARGETED_THRESHOLD:
        return (
            False,
            f"changeset too large ({len(modified_py_files)} files > {TARGETED_THRESHOLD} threshold)",
        )
    for filepath in modified_py_files:
        inner = filepath.removeprefix(prefix)
        if not (dest_base / inner).exists():
            return (False, f"destination file missing: {filepath}")
    return (True, "")


def _deploy_targeted(
    modified_files: list[str],
    source_base: Path,
    dest_base: Path,
    site: SiteInfo,
    prefix: str,
) -> tuple[StepTiming, ...] | None:
    """Deploy individual Python files; returns step timings or None on failure."""
    rec = _StepRecorder()
    rec.begin()

    # Step 1: Edition filter (per-file path check)
    filtered = filter_edition_files(modified_files, site.edition)
    rec.record("edition_chk", file_count=len(modified_files))

    if not filtered:
        return rec.freeze()

    # Step 2: Copy files
    current_file = ""
    try:
        for current_file in filtered:
            inner = current_file.removeprefix(prefix)
            src = source_base / inner
            dst = dest_base / inner
            shutil.copy2(src, dst)
    except OSError as e:
        output.warn(f"Targeted copy failed for {current_file}: {e}, falling back to full copy")
        return None
    rec.record("copy", file_count=len(filtered))

    # Step 3: Compile bytecode (single subprocess call for all files)
    site_python = site.root / "bin" / "python3"
    if site_python.exists():
        dest_paths = [str(dest_base / f.removeprefix(prefix)) for f in filtered]
        result = subprocess.run(
            [str(site_python), "-m", "compileall", "-qq", *dest_paths],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            output.error(f"compileall reported errors:\n{result.stderr.strip()}")
    else:
        output.error(f"Site Python not found at {site_python} -- bytecode compilation skipped.")
    rec.record("py_compile", file_count=len(filtered))

    return rec.freeze()


# ---------------------------------------------------------------------------
# Copy excludes for wheel source deployment
# ---------------------------------------------------------------------------

_WHEEL_COPY_EXCLUDES: tuple[str, ...] = (
    "*.pyc",
    "__pycache__",
    ".mypy_cache",
    "tests",
    "test",
    ".f12",
    "BUILD",
    "setup.cfg",
    "pyproject.toml",
    "*.in",
    "run",
    "OWNERS",
    "dev-requirements*",
    ".git*",
)


# ---------------------------------------------------------------------------
# Parent-child subdir helpers
# ---------------------------------------------------------------------------


def _subdirs_overlap(subdirs_a: Iterable[str], subdirs_b: Iterable[str]) -> bool:
    """Return True if any subdir in *a* is a parent or child of any in *b*.

    Detects both exact matches and hierarchical relationships so that
    packages with nested source_subdirs (e.g. ``cmk/licensing/`` and
    ``cmk/licensing/nonfree/``) are recognised as co-dependent.
    """
    normed_b = [s.rstrip("/") + "/" for s in subdirs_b]
    for a in subdirs_a:
        a_n = a.rstrip("/") + "/"
        for b_n in normed_b:
            if a_n.startswith(b_n) or b_n.startswith(a_n):
                return True
    return False


def _compute_protected_children(
    specs: Iterable[WheelDeploySpec],
) -> dict[str, frozenset[str]]:
    """Map each package to subdirs from OTHER packages nested inside its own.

    Used by ``_clean_package`` to avoid ``shutil.rmtree`` on parent
    directories that contain child packages deployed by a sibling spec.
    """
    specs_list = list(specs)
    result: dict[str, frozenset[str]] = {}
    for spec in specs_list:
        protected: set[str] = set()
        for other in specs_list:
            if other.package == spec.package:
                continue
            for own_sd in spec.source_subdirs:
                own_n = own_sd.rstrip("/") + "/"
                for other_sd in other.source_subdirs:
                    other_n = other_sd.rstrip("/") + "/"
                    if other_n.startswith(own_n) and other_n != own_n:
                        protected.add(other_sd)
        if protected:
            result[spec.package] = frozenset(protected)
    return result


def _selective_rmtree(root: Path, protected: set[Path]) -> None:
    """Remove directory contents except protected subtrees.

    Walks *root* non-recursively.  Entries that *are* a protected path (or
    live inside one) are left untouched.  Directories that *contain* a
    protected path are recursed into rather than removed wholesale.
    """
    for entry in list(root.iterdir()):
        if any(entry == p or entry.is_relative_to(p) for p in protected):
            continue
        if entry.is_dir():
            if any(p.is_relative_to(entry) for p in protected):
                _selective_rmtree(entry, protected)
            else:
                shutil.rmtree(entry)
        else:
            entry.unlink()


# ---------------------------------------------------------------------------
# Clean-then-deploy
# ---------------------------------------------------------------------------


def _clean_package(
    site_packages: Path,
    subdirs: list[str],
    dist_info_glob: str,
    *,
    shared_subdirs: frozenset[str] = frozenset(),
    protected_children: frozenset[str] = frozenset(),
) -> None:
    """Remove package directories and stale .dist-info before fresh deploy.

    Shared subdirs (deployed by multiple packages) are skipped -- copytree
    with ``dirs_exist_ok=True`` handles the overwrite instead.

    When *protected_children* is non-empty, subdirs that contain a protected
    child are cleaned selectively (files removed, protected subtrees kept)
    rather than via ``shutil.rmtree``.
    """
    for subdir in subdirs:
        if subdir in shared_subdirs:
            continue  # copytree with dirs_exist_ok handles overwrite
        target = site_packages / subdir.rstrip("/")
        if target.is_dir():
            # Find children of this target that must be preserved
            protected_abs = {
                site_packages / c.rstrip("/")
                for c in protected_children
                if (c.rstrip("/") + "/").startswith(subdir.rstrip("/") + "/")
                and c.rstrip("/") != subdir.rstrip("/")
            }
            if protected_abs:
                _selective_rmtree(target, protected_abs)
            else:
                shutil.rmtree(target)
        elif target.is_file():
            target.unlink()

    # Clean __pycache__ dirs under each subdir's parent.
    # ignore_errors handles OverlayFS whiteout entries that appear in
    # glob results but cannot actually be removed.
    for subdir in subdirs:
        parent = site_packages / Path(subdir.rstrip("/")).parent
        if parent.is_dir():
            for pycache in parent.glob("__pycache__"):
                shutil.rmtree(pycache, ignore_errors=True)

    # Remove all matching .dist-info directories
    for di in site_packages.glob(dist_info_glob):
        if di.is_dir():
            shutil.rmtree(di)


# ---------------------------------------------------------------------------
# Copy package sources
# ---------------------------------------------------------------------------


def _copy_package_tree(
    source: Path,
    dest: Path,
    excludes: list[str] | None = None,
) -> None:
    """Copy a package subdirectory to site-packages with exclude filtering."""
    patterns = excludes or _WHEEL_COPY_EXCLUDES
    shutil.copytree(
        source,
        dest,
        ignore=shutil.ignore_patterns(*patterns),
        dirs_exist_ok=True,
    )


# ---------------------------------------------------------------------------
# .dist-info generation (PEP 376/427)
# ---------------------------------------------------------------------------


def _file_hash_record(filepath: Path) -> tuple[str, str]:
    """Compute ``(sha256_hash, size)`` for a PEP 376 RECORD entry.

    Uses SHA256 with base64url encoding as required by the RECORD format
    (PEP 376). This differs from ``deploy_state.compute_file_hash`` which
    uses hex-encoded SHA256 for incremental state tracking.
    """
    content = filepath.read_bytes()
    digest = hashlib.sha256(content).digest()
    hash_str = "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return hash_str, str(len(content))


def _generate_dist_info(
    site_packages: Path,
    distribution_name: str,
    version: str,
    top_level_packages: list[str],
    installed_files: list[Path],
) -> None:
    """Generate minimal PEP 376-compliant .dist-info (METADATA, WHEEL, RECORD, top_level.txt)."""
    # Normalize name: dashes -> underscores
    normalized = distribution_name.replace("-", "_")
    dist_info_dir = site_packages / f"{normalized}-{version}.dist-info"
    dist_info_dir.mkdir(parents=True, exist_ok=True)

    # METADATA
    metadata = dist_info_dir / "METADATA"
    metadata.write_text(f"Metadata-Version: 2.1\nName: {distribution_name}\nVersion: {version}\n")

    # WHEEL
    wheel = dist_info_dir / "WHEEL"
    wheel.write_text(
        "Wheel-Version: 1.0\nGenerator: cmk-dev-deploy\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )

    # top_level.txt
    top_level = dist_info_dir / "top_level.txt"
    top_level.write_text("\n".join(top_level_packages) + "\n")

    # RECORD (CSV with sha256 hashes per PEP 376)
    record_path = dist_info_dir / "RECORD"
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")

    # Installed files
    for filepath in installed_files:
        if filepath.is_file():
            rel = filepath.relative_to(site_packages)
            h, size = _file_hash_record(filepath)
            writer.writerow([str(rel), h, size])

    # dist-info files themselves
    for meta_file in [metadata, wheel, top_level]:
        rel = meta_file.relative_to(site_packages)
        h, size = _file_hash_record(meta_file)
        writer.writerow([str(rel), h, size])

    # RECORD's own entry has empty hash
    writer.writerow([str(record_path.relative_to(site_packages)), "", ""])
    record_path.write_text(buf.getvalue())


# ---------------------------------------------------------------------------
# Bytecode compilation
# ---------------------------------------------------------------------------


def _compile_bytecode(site_python: Path, dirs: list[Path]) -> bool:
    """Compile Python bytecode via single ``compileall -qq`` invocation."""
    if not dirs:
        return True

    if not site_python.exists():
        output.error(
            f"Site Python not found at {site_python} -- bytecode compilation skipped.\n"
            "  The site will not work without compiled bytecode."
        )
        return False

    cmd = [str(site_python), "-m", "compileall", "-qq"]
    cmd.extend(str(d) for d in dirs)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        output.error(f"compileall reported errors:\n{result.stderr.strip()}")
        return False

    return True


# ---------------------------------------------------------------------------
# Per-package state key computation
# ---------------------------------------------------------------------------


def _deployer_keys(spec: WheelDeploySpec) -> list[tuple[str, tuple[str, ...]]]:
    """Return (state_key, path_prefixes) pairs for a wheel spec."""
    if spec.source_subdirs:
        prefixes = tuple(f"{spec.package}/{sd}" for sd in spec.source_subdirs)
    else:
        prefixes = (spec.package + "/",)
    return [(f"wheel:{spec.package}", prefixes)]


# ---------------------------------------------------------------------------
# Collect installed files for a directory tree
# ---------------------------------------------------------------------------


def _collect_installed_files(base: Path) -> list[Path]:
    """Collect all files under base directory (recursively)."""
    if base.is_file():
        return [base]
    if not base.is_dir():
        return []
    return sorted(base.rglob("*"))


# ---------------------------------------------------------------------------
# Deploy a single distribution (copy mode)
# ---------------------------------------------------------------------------


def _leaf_subdirs(
    subdirs: tuple[str, ...], repo_root: Path | None = None, package_dir: str = ""
) -> tuple[str, ...]:
    """Filter out namespace-only parent dirs that have children in the list.

    Prevents cleaning/copying shared namespace dirs (e.g. ``cmk/plugins/``)
    that would destroy other packages' content.
    """
    normalized = [s.rstrip("/") + "/" for s in subdirs]
    result: list[str] = []
    for s, n in zip(subdirs, normalized):
        has_children = any(other.startswith(n) and other != n for other in normalized)
        if not has_children:
            result.append(s)
            continue
        # Parent with children: keep only if it has direct files in source
        if repo_root is not None and package_dir:
            source = repo_root / package_dir / s.rstrip("/")
            if source.is_dir() and any(f.is_file() for f in source.iterdir()):
                result.append(s)
                continue
        # No source to check or no direct files — skip this parent
    return tuple(result)


def _deploy_single_distribution(
    dist_info: _DistributionInfo,
    repo_root: Path,
    package_dir: str,
    file_root: Path,
    *,
    dist_info_root: Path | None = None,
    shared_subdirs: frozenset[str] = frozenset(),
    protected_children: frozenset[str] = frozenset(),
) -> list[Path]:
    """Deploy a single distribution: clean -> copy -> .dist-info."""
    effective_dist_info_root = dist_info_root if dist_info_root is not None else file_root
    normalized = dist_info.distribution_name.replace("-", "_")
    dist_info_glob = f"{normalized}-*.dist-info"

    # Filter out namespace-only parent dirs that have children.  When subdirs
    # contain both a parent namespace (e.g. ``cmk/plugins/``) and a child
    # package (e.g. ``cmk/plugins/metric_backend_omd/``), cleaning/copying
    # the parent with --delete would destroy other packages' content.
    leaf_subdirs = _leaf_subdirs(dist_info.source_subdirs, repo_root, package_dir)

    # Clean target subdirs and stale .dist-info
    _clean_package(
        file_root,
        list(leaf_subdirs),
        dist_info_glob,
        shared_subdirs=shared_subdirs,
        protected_children=protected_children,
    )
    # Also clean dist-info from its actual root when it differs from file_root
    if dist_info_root is not None:
        for di in effective_dist_info_root.glob(dist_info_glob):
            if di.is_dir():
                shutil.rmtree(di)

    # Copy each source subdir
    deployed_paths: list[Path] = []
    all_installed_files: list[Path] = []

    for subdir in leaf_subdirs:
        source = repo_root / package_dir / subdir.rstrip("/")
        dest = file_root / subdir.rstrip("/")

        if subdir.endswith(".py"):
            # Flat file case: copy single file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            all_installed_files.append(dest)
            deployed_paths.append(dest)
        else:
            # Directory case: copytree
            dest.mkdir(parents=True, exist_ok=True)
            _copy_package_tree(source, dest)
            all_installed_files.extend(_collect_installed_files(dest))
            deployed_paths.append(dest)

    # Generate .dist-info
    _generate_dist_info(
        effective_dist_info_root,
        dist_info.distribution_name,
        _DIST_INFO_VERSION,
        list(dist_info.top_level_packages),
        all_installed_files,
    )

    return deployed_paths


# ---------------------------------------------------------------------------
# Category D: Generated-source packages (bazel build + zipfile extraction)
# ---------------------------------------------------------------------------


def _get_execution_root(repo_root: Path) -> Path:
    """Retrieve Bazel execution root via ``bazel info execution_root``."""
    return Path(
        run_checked(
            ["bazel", "info", "execution_root"],
            cwd=repo_root,
            timeout=BAZEL_INFO,
            error_cls=WheelDeployError,
            description="bazel info execution_root",
            recovery="Check Bazel server health with 'bazel info'.",
        ).stdout.strip()
    )


def _build_and_extract_wheel(
    package_dir: str,
    target: str,
    repo_root: Path,
    site_packages: Path,
) -> list[Path]:
    """Build a generated-source wheel via Bazel and extract to site-packages.

    For packages with no Python source in the repo (cmk-shared-typing,
    cmc-protocols). Builds the wheel, locates it via cquery, and extracts
    Python source files directly (skipping .dist-info from the wheel).
    """
    label = f"//{package_dir}{target}"

    # 1. Build the wheel
    run_checked(
        ["bazel", "build", label],
        cwd=repo_root,
        timeout=BAZEL_WHEEL_BUILD,
        error_cls=WheelDeployError,
        description=f"bazel build {label}",
        recovery="Retry -- wheel builds are usually fast but Bazel server may be cold.",
    )

    # 2. Find wheel path via cquery
    result = run_checked(
        [
            "bazel",
            "cquery",
            label,
            "--output=starlark",
            "--starlark:expr=target.files.to_list()[0].path",
        ],
        cwd=repo_root,
        timeout=BAZEL_CQUERY_QUICK,
        error_cls=WheelDeployError,
        description=f"bazel cquery for {label}",
        recovery="Retry -- Bazel server may need warming up.",
    )
    relative_path = result.stdout.strip()
    if not relative_path:
        raise WheelDeployError(
            f"bazel cquery returned empty output for {label}",
            recovery="Ensure the wheel target produces a .whl output.",
        )

    # 3. Resolve against execution root
    execution_root = _get_execution_root(repo_root)
    wheel_path = execution_root / relative_path
    if not wheel_path.exists():
        raise WheelDeployError(
            f"Wheel file not found: {wheel_path}",
            recovery=f"Expected .whl at {wheel_path}. Ensure the build completed.",
        )

    # 4. Extract Python source files (skip .dist-info entries from the wheel)
    extracted_files: list[Path] = []
    with zipfile.ZipFile(wheel_path, "r") as zf:
        for member in zf.namelist():
            # Skip .dist-info directory entries from inside the wheel
            if ".dist-info/" in member or member.endswith(".dist-info"):
                continue
            # Skip directories
            if member.endswith("/"):
                continue
            target_path = site_packages / member
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(target_path, "wb") as dst:
                dst.write(src.read())
            extracted_files.append(target_path)

    return extracted_files


# ---------------------------------------------------------------------------
# Deploy a package group (all distributions for one WheelDeploySpec)
# ---------------------------------------------------------------------------


def _deploy_package_group(
    spec: WheelDeploySpec,
    pkg_info: _PackageInfo,
    repo_root: Path,
    site_packages: Path,
    site: SiteInfo,
    *,
    file_root: Path | None = None,
    dist_info_root: Path | None = None,
    shared_subdirs: frozenset[str] = frozenset(),
    protected_children: frozenset[str] = frozenset(),
) -> list[Path]:
    """Deploy all distributions for a single WheelDeploySpec.

    Dispatches to direct copy or bazel+extract based on deploy_mode.
    Applies edition directory pruning when ``spec.edition_filter`` is True.
    """
    effective_file_root = file_root if file_root is not None else site_packages
    all_deployed: list[Path] = []

    for dist in pkg_info.distributions:
        if dist.deploy_mode == WheelDeployMode.GENERATED:
            # Category D: bazel build + zipfile extraction
            normalized = dist.distribution_name.replace("-", "_")
            dist_info_glob = f"{normalized}-*.dist-info"

            # Clean existing .dist-info (we don't know the source subdirs
            # for generated packages, so only clean dist-info)
            for di in site_packages.glob(dist_info_glob):
                if di.is_dir():
                    shutil.rmtree(di)

            extracted = _build_and_extract_wheel(
                spec.package,
                dist.bazel_target,
                repo_root,
                site_packages,
            )

            # Generate .dist-info for the extracted files
            _generate_dist_info(
                site_packages,
                dist.distribution_name,
                _DIST_INFO_VERSION,
                list(dist.top_level_packages),
                extracted,
            )

            # Collect unique parent directories for compileall
            seen_dirs: set[Path] = set()
            for f in extracted:
                parent = f.parent
                if parent not in seen_dirs:
                    seen_dirs.add(parent)
                    all_deployed.append(parent)
        else:
            # Categories A, B, C, E: direct / flat / dynamic
            deployed = _deploy_single_distribution(
                dist,
                repo_root,
                spec.package,
                effective_file_root,
                dist_info_root=dist_info_root,
                shared_subdirs=shared_subdirs,
                protected_children=protected_children,
            )
            all_deployed.extend(deployed)

    # Post-copy edition filtering (for packages like cmk/ with nonfree dirs)
    if spec.edition_filter:
        for deployed_path in all_deployed:
            if deployed_path.is_dir():
                filter_editions(deployed_path, site.edition)

    return all_deployed


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def specs_for_changed_files(
    changed_files: tuple[str, ...],
    all_specs: tuple[WheelDeploySpec, ...] | None = None,
) -> tuple[WheelDeploySpec, ...]:
    """Return only the specs whose package prefix matches any changed file."""
    if all_specs is None:
        all_specs = get_wheel_specs()

    matched: set[str] = set()
    for spec in all_specs:
        prefix = spec.package + "/"
        if any(f.startswith(prefix) for f in changed_files):
            matched.add(spec.package)

    return tuple(s for s in all_specs if s.package in matched)


def _remove_deleted_files(
    deleted_files: tuple[str, ...],
    specs: list[WheelDeploySpec],
    site_packages: Path,
    site: SiteInfo,
) -> None:
    """Remove files from deploy targets that were deleted between commits."""
    removed = 0
    for spec in specs:
        file_root, _di_root = _get_deploy_roots(spec, site, site_packages)
        prefix = spec.package + "/"
        for deleted in deleted_files:
            if not deleted.startswith(prefix):
                continue
            rel = deleted[len(prefix) :]
            # Check the file falls within a deployed subdir
            if not any(rel.startswith(sd) for sd in spec.source_subdirs):
                continue
            target = file_root / rel
            if target.is_file():
                target.unlink()
                removed += 1
                # Also remove .pyc
                pyc = (
                    target.parent
                    / "__pycache__"
                    / (target.stem + f".{sys.implementation.cache_tag}.pyc")
                )
                if pyc.is_file():
                    pyc.unlink()
    if removed:
        output.verbose(f"  Removed {removed} deleted file(s) from deploy targets")


def _expand_co_dependents(
    candidates: tuple[WheelDeploySpec, ...],
    all_specs: tuple[WheelDeploySpec, ...],
) -> tuple[WheelDeploySpec, ...]:
    """Expand candidates to include packages sharing deployed subdirectories.

    Ensures packages whose subdirs would be cleaned by a candidate are also
    redeployed, preventing file loss.
    """
    if not candidates:
        return candidates

    candidate_packages = {s.package for s in candidates}

    # Collect all subdirs touched by candidates
    candidate_subdirs: set[str] = set()
    for spec in candidates:
        candidate_subdirs.update(spec.source_subdirs)

    # Find all specs (not yet selected) that share or overlap a subdir.
    # Uses prefix matching to detect parent-child relationships (e.g.
    # cmk/licensing/ and cmk/licensing/nonfree/ from different packages).
    extra_packages: set[str] = set()
    for spec in all_specs:
        if spec.package in candidate_packages:
            continue
        if _subdirs_overlap(spec.source_subdirs, candidate_subdirs):
            extra_packages.add(spec.package)

    if not extra_packages:
        return candidates

    return tuple(
        s for s in all_specs if s.package in candidate_packages or s.package in extra_packages
    )


def deploy_wheels(
    changes: ChangeSet | None,
    repo_root: Path,
    site: SiteInfo,
    *,
    state: DeployState | None = None,
) -> WheelDeployResult:
    """Deploy Python wheel packages to the OMD site via direct copy.

    Single public entry point: filters specs, checks incremental state,
    deploys in parallel, runs compileall, and persists per-package state.
    """
    import time as _time

    from cmk.dev_deploy.state.deploy_state import DeployerState

    start = _time.monotonic()

    # 1. Determine active specs
    if changes is None:
        active_candidates = get_wheel_specs()
    else:
        active_candidates = specs_for_changed_files(changes.files)
        # Expand to include co-dependent packages: if package A cleans a
        # subdir that package B also deploys into, B must be redeployed
        # to restore its files.
        active_candidates = _expand_co_dependents(active_candidates, get_wheel_specs())

    # Build index of shared subdirs (used by multiple packages).
    # For shared subdirs, _clean_package skips rmtree to avoid destroying
    # other packages' files; copytree with dirs_exist_ok handles overwrite.
    _subdir_owners: dict[str, int] = {}
    for spec in active_candidates:
        for sd in spec.source_subdirs:
            _subdir_owners[sd] = _subdir_owners.get(sd, 0) + 1
    shared_subdirs = frozenset(sd for sd, count in _subdir_owners.items() if count > 1)

    # 2. Filter by edition and source directory existence
    active_specs: list[WheelDeploySpec] = []
    skipped_edition = 0
    skipped_missing = 0

    for spec in active_candidates:
        if not site.edition.matches(spec.edition_constraint):
            skipped_edition += 1
            continue

        if not (repo_root / spec.package).is_dir():
            skipped_missing += 1
            continue

        active_specs.append(spec)

    if not active_specs:
        elapsed = _time.monotonic() - start
        return WheelDeployResult(
            wheels_deployed=0,
            wheels_skipped=0,
            wheels_skipped_edition=skipped_edition,
            wheels_skipped_missing=skipped_missing,
            elapsed=elapsed,
            per_package_states={},
        )

    # Discover site-packages path
    site_packages = get_site_packages(site)

    # Compute protected children: subdirs from OTHER active packages nested
    # inside a given package's own subdirs.  Passed to _clean_package so that
    # rmtree on a parent dir (e.g. cmk/licensing/) preserves child dirs owned
    # by a sibling package (e.g. cmk/licensing/nonfree/).
    all_protected = _compute_protected_children(active_specs)

    # Get current HEAD commit once
    head = get_head_commit(repo_root)

    # 3. Partition specs into deploy vs skip
    to_deploy: list[tuple[WheelDeploySpec, _PackageInfo]] = []
    skipped_count = 0

    for spec in active_specs:
        # Per-distribution skip check: all distributions must be unchanged to skip
        keys_and_prefixes = _deployer_keys(spec)
        all_skip = True
        skip_results: list[SkipResult] = []
        for dist_key, _dist_prefixes in keys_and_prefixes:
            result = check_skip(dist_key, repo_root, site.root, state, head)
            skip_results.append(result)
            if not result.should_skip:
                all_skip = False
                break
        if all_skip:
            skipped_count += 1
            # Use the first result's reason for the skip message
            first_result = skip_results[0]
            if first_result.paths_checked == () and "HEAD fallback" in first_result.reason:
                output.verbose(f"{spec.package}: using global check (no source paths)")
            output.verbose(f"{spec.package}: skipped ({first_result.reason})")
            continue

        # Resolve package info from spec metadata + disk discovery
        pkg_info = _build_package_info_from_spec(spec, repo_root)

        if pkg_info is None:
            output.warn(f"Could not resolve deployment info for {spec.package} -- skipping")
            skipped_missing += 1
            continue

        to_deploy.append((spec, pkg_info))

    if not to_deploy:
        elapsed = _time.monotonic() - start
        return WheelDeployResult(
            wheels_deployed=0,
            wheels_skipped=skipped_count,
            wheels_skipped_edition=skipped_edition,
            wheels_skipped_missing=skipped_missing,
            elapsed=elapsed,
            per_package_states={},
        )

    # 4a. Attempt targeted deploy for packages with small changesets.
    # Considers ALL changes not yet deployed: both committed (HEAD vs
    # build_commit) and uncommitted (working tree vs HEAD), filtered to
    # each package's deployed source_subdirs.
    step_timings: tuple[StepTiming, ...] = ()
    targeted_packages: set[str] = set()

    targeted_batch: list[tuple[str, tuple[str, ...], float]] = []

    for spec, pkg_info in to_deploy:
        if changes is None or spec.deploy_mode != WheelDeployMode.DIRECT:
            continue

        prefix = spec.package + "/"

        file_root, _di_root = _get_deploy_roots(spec, site, site_packages)
        dest_base = file_root

        # Filter the full changeset (build_commit..working tree) to only
        # .py files within this package's deployed source_subdirs.
        classify_reason = ""
        deployed_dir_prefixes = tuple(prefix + sd for sd in spec.source_subdirs if sd.endswith("/"))
        deployed_file_entries = frozenset(
            prefix + sd for sd in spec.source_subdirs if sd.endswith(".py")
        )
        pkg_modified = []
        for f in changes.files:
            in_dir = any(f.startswith(dp) for dp in deployed_dir_prefixes)
            is_file = f in deployed_file_entries
            if not in_dir and not is_file:
                continue
            if f.endswith(".py"):
                pkg_modified.append(f)
            else:
                # Non-.py change in a deployed subdir needs full deploy
                classify_reason = f"non-Python change in deployed path: {f}"
                break

        eligible, _reason = _can_use_targeted(pkg_modified, classify_reason, dest_base, prefix)
        if eligible:
            # Skip if another spec for the same package was already targeted
            if spec.package in targeted_packages:
                continue
            timings = _deploy_targeted(
                pkg_modified, repo_root / spec.package, dest_base, site, prefix
            )
            if timings is not None:
                step_timings = timings
                targeted_packages.add(spec.package)
                targeted_batch.append(
                    (spec.package, tuple(pkg_modified), sum(t.elapsed for t in timings))
                )
    # targeted_batch output is deferred to after all threads finish

    # Filter out targeted packages from full deploy list
    to_deploy_full = [
        (spec, pkg_info) for spec, pkg_info in to_deploy if spec.package not in targeted_packages
    ]

    # Merge specs with the same package into a single deploy operation to
    # avoid race conditions when multiple wheel targets share a source dir
    # (e.g. cmk-livestatus-client has :cmk-livestatus-client_whl and :livestatus_whl
    # both deploying into cmk/livestatus_client/).
    merged_deploy: dict[str, tuple[WheelDeploySpec, _PackageInfo, list[WheelDeploySpec]]] = {}
    for spec, pkg_info in to_deploy_full:
        if spec.package in merged_deploy:
            existing_spec, existing_info, extra_specs = merged_deploy[spec.package]
            # Deduplicate distributions by name
            existing_names = {d.distribution_name for d in existing_info.distributions}
            new_dists = tuple(
                d for d in pkg_info.distributions if d.distribution_name not in existing_names
            )
            merged_info = _PackageInfo(
                distributions=existing_info.distributions + new_dists,
            )
            extra_specs.append(spec)
            merged_deploy[spec.package] = (existing_spec, merged_info, extra_specs)
        else:
            merged_deploy[spec.package] = (spec, pkg_info, [])
    to_deploy_merged = list(merged_deploy.values())

    # 4b. Deploy non-skipped, non-targeted packages in parallel
    all_compiled_dirs: list[Path] = []
    per_package_states: dict[str, DeployerState] = {}
    wheels_deployed = len(targeted_packages)
    full_deploy_results: list[tuple[str, float]] = []

    if to_deploy_merged:
        max_workers = min(4, len(to_deploy_merged))

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for spec, pkg_info, extra_specs in to_deploy_merged:
                fr, dir_ = _get_deploy_roots(spec, site, site_packages)
                futures[
                    pool.submit(
                        _deploy_and_report,
                        spec,
                        pkg_info,
                        repo_root,
                        site_packages,
                        site,
                        shared_subdirs,
                        fr,
                        dir_,
                        all_protected.get(spec.package, frozenset()),
                    )
                ] = (spec, extra_specs)

            for future in as_completed(futures):
                spec, extra_specs = futures[future]
                deployed_dirs, pkg_elapsed = future.result()
                all_compiled_dirs.extend(deployed_dirs)
                wheels_deployed += 1
                full_deploy_results.append((spec.package, pkg_elapsed))

                # Build per-distribution state entries for all merged specs
                all_specs = [spec] + extra_specs
                for s in all_specs:
                    for dist_key, dist_prefixes in _deployer_keys(s):
                        dist_dirty = compute_dirty_hashes(repo_root, path_prefixes=dist_prefixes)
                        per_package_states[dist_key] = DeployerState(
                            deployer=dist_key,
                            git_commit=head,
                            dirty_file_hashes=dist_dirty,
                            deployed_at=_time.time(),
                        )

    # Build state entries for targeted packages too
    for spec, _pkg_info in to_deploy:
        if spec.package in targeted_packages:
            for dist_key, dist_prefixes in _deployer_keys(spec):
                dist_dirty = compute_dirty_hashes(repo_root, path_prefixes=dist_prefixes)
                per_package_states[dist_key] = DeployerState(
                    deployer=dist_key,
                    git_commit=head,
                    dirty_file_hashes=dist_dirty,
                    deployed_at=_time.time(),
                )

    # 4c. Remove files deleted between commits from site-packages.
    # Only touches files within known wheel subdirs to avoid removing
    # site config or user data.
    if changes is not None and changes.deleted_files:
        _remove_deleted_files(changes.deleted_files, list(get_wheel_specs()), site_packages, site)

    # 5. Run compileall ONCE on all deployed dirs
    if all_compiled_dirs:
        site_python = site.root / "bin" / "python3"
        # Deduplicate directories
        unique_dirs = list(dict.fromkeys(all_compiled_dirs))
        _compile_bytecode(site_python, unique_dirs)

    # Print consolidated per-package output (targeted + full) after all
    # threads finish so it doesn't interleave with the spinner.
    if targeted_batch:
        output.print_targeted_deploy_batch(targeted_batch)
    if full_deploy_results:
        full_deploy_results.sort(key=lambda x: x[0])
        for pkg_name, pkg_elapsed in full_deploy_results:
            output.print_wheel_full_deploy(pkg_name, pkg_elapsed)

    elapsed = _time.monotonic() - start

    return WheelDeployResult(
        wheels_deployed=wheels_deployed,
        wheels_skipped=skipped_count,
        wheels_skipped_edition=skipped_edition,
        wheels_skipped_missing=skipped_missing,
        elapsed=elapsed,
        per_package_states=per_package_states,
        step_timings=step_timings,
    )


def _deploy_and_report(
    spec: WheelDeploySpec,
    pkg_info: _PackageInfo,
    repo_root: Path,
    site_packages: Path,
    site: SiteInfo,
    shared_subdirs: frozenset[str] = frozenset(),
    file_root: Path | None = None,
    dist_info_root: Path | None = None,
    protected_children: frozenset[str] = frozenset(),
) -> tuple[list[Path], float]:
    """Thread-safe wrapper around _deploy_package_group with timing."""
    pkg_start = time.monotonic()

    try:
        deployed = _deploy_package_group(
            spec,
            pkg_info,
            repo_root,
            site_packages,
            site,
            file_root=file_root,
            dist_info_root=dist_info_root,
            shared_subdirs=shared_subdirs,
            protected_children=protected_children,
        )
    except Exception as exc:
        subdirs = [d.source_subdirs for d in pkg_info.distributions]
        raise type(exc)(f"{spec.package} ({spec.deploy_mode}): {exc} [subdirs={subdirs}]") from exc

    pkg_elapsed = time.monotonic() - pkg_start

    return deployed, pkg_elapsed
