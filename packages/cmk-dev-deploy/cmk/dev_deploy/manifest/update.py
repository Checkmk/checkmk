# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Build the deploy manifest from auto-discovered Bazel targets and TOML overrides.

Auto-discovers config specs from ``deps_packages`` packaging targets and the
deployed wheel prefixes from ``//:deploy-python``.  Manual specs
(package/service) are loaded from ``deploy_specs.toml``.  Enriches sentinel
fields from ``bazel cquery`` data, computes cross-deployer dependency edges
(deploy_deps), and writes the resulting JSON manifest for the deploy tool.

Usage (from repo root)::

    PYTHONPATH=packages/cmk-dev-deploy python -m cmk.dev_deploy.manifest.update
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.bazel import bazel_command
from cmk.dev_deploy.core.output import Spinner
from cmk.dev_deploy.manifest.reader import MANIFEST_VERSION
from cmk.dev_deploy.manifest.staleness import save_manifest_hashes
from cmk.dev_deploy.types import CategorizationRule, ChangeCategory, DeployMethod

logger = logging.getLogger(__name__)

MANIFEST_REPO_PATH = "packages/cmk-dev-deploy/cmk/dev_deploy/manifest/deploy_manifest.json"


def specs_path() -> Path:
    """Return the path to the deploy specs TOML file."""
    return Path(__file__).parent / "deploy_specs.toml"


_QUERY_TIMEOUT = 120

# Editions that include non-free code.  Auto-derived from paths containing
# "non-free/" or "nonfree/" instead of being declared in deploy specs.
_NONFREE_EDITIONS: tuple[str, ...] = ("cloud", "pro", "ultimate", "ultimatemt")

# Known config deploy targets and their methods, keyed by package_target.
# Auto-classification rules:
#   - targets under active_checks/, notifications/ with explicit file modes → install_files
#   - targets under agents/, notifications/templates/ → copy_dir
#   - targets under locale/ → locale_compile
_CONFIG_METHOD_RULES: MappingProxyType[str, str] = MappingProxyType(
    {
        "active_checks": "install_files",
        "locale": "locale_compile",
    }
)

# ---------------------------------------------------------------------------
# Categorization rule derivation
# ---------------------------------------------------------------------------

# Extension-to-category priority: checked in order, first match wins.
# Used by _extensions_to_category() to derive a ChangeCategory from the set
# of file extensions found in a Bazel target's source files.
_EXTENSION_CATEGORY_PRIORITY: tuple[tuple[frozenset[str], ChangeCategory], ...] = (
    (frozenset({".rs"}), ChangeCategory.RUST),
    (frozenset({".cc", ".h", ".hpp", ".proto"}), ChangeCategory.CPP),
    (frozenset({".vue"}), ChangeCategory.VUE),
    (frozenset({".js", ".ts", ".tsx", ".css", ".scss"}), ChangeCategory.FRONTEND),
)


def _load_supplementary_rules(toml_path: Path) -> tuple[CategorizationRule, ...]:
    """Load supplementary categorization rules from deploy_specs.toml.

    These cover packages and directories that have no install/wheel/config
    spec in the manifest but still need categorization rules (e.g., agent-side
    Rust binaries, catch-all directory prefixes).
    """
    with open(toml_path, "rb") as f:
        raw = tomllib.load(f)

    rules: list[CategorizationRule] = []
    for entry in raw.get("categorization", []):
        prefix = entry["prefix"]
        category_str = entry["category"]
        extensions_raw = entry.get("extensions")

        category = ChangeCategory(category_str)
        extensions = frozenset(extensions_raw) if extensions_raw is not None else None
        rules.append(CategorizationRule(prefix, extensions, category))

    return tuple(rules)


def _derive_editions(source_prefix: str, package_target: str) -> Sequence[str]:
    """Derive edition constraint from path analysis.

    Returns _NONFREE_EDITIONS if either path contains a non-free marker,
    empty list otherwise (meaning all editions).
    """
    if (
        "non-free/" in package_target
        or "/nonfree/" in source_prefix
        or source_prefix.startswith(("non-free/", "nonfree/"))
    ):
        return _NONFREE_EDITIONS
    return []


# ---------------------------------------------------------------------------
# TOML spec loading (manual specs only: package + service)
# ---------------------------------------------------------------------------


def _load_specs_from_toml(
    specs_path: Path,
    is_nonfree_checkout: bool,
) -> dict[str, Any]:
    """Load manual deploy specs from TOML (package and service only).

    Wheel and config specs are now auto-discovered from Bazel.
    Only package (compiled artifact) and service specs remain in the TOML.

    Also loads config_overrides for merging with auto-discovered config specs.

    Args:
        specs_path: Path to deploy_specs.toml.
        is_nonfree_checkout: True if repo has non-free/ directory.

    Returns:
        Dict with install_specs, service_specs, and config_overrides keys.
    """
    with open(specs_path, "rb") as f:
        raw = tomllib.load(f)

    install_specs: list[dict[str, Any]] = []
    for entry in raw.get("package", []):
        package_target = entry["package_target"]
        install_specs.append(
            {
                "editions": _derive_editions("", package_target),
                "frontend_supervised": entry.get("frontend_supervised", False),
                "input_prefixes": [],
                "mode": -1,
                "name": entry["name"],
                "needs_faked_artifacts": entry.get("needs_faked_artifacts", False),
                "needs_version_flag": entry.get("needs_version_flag", False),
                "output_basename": entry.get("output_basename", ""),
                "package_target": package_target,
                "post_install": entry.get("post_install", []),
                "site_dest": entry.get("site_dest", ""),
                "source_prefix": "",
                "use_copytree": entry.get("use_copytree", False),
            }
        )

    service_specs: list[dict[str, Any]] = []
    for entry in raw.get("service", []):
        package_target = entry["package_target"]
        # Derive source_prefix from package_target when not explicitly set
        source_prefix = entry.get("source_prefix") or _label_to_package_path(package_target)
        service_specs.append(
            {
                "editions": _derive_editions(source_prefix, package_target),
                "name": entry["name"],
                "package_target": package_target,
                "services": entry["services"],
                "source_prefix": source_prefix,
            }
        )

    # Load config overrides (keyed by package_target label)
    config_overrides: dict[str, dict[str, Any]] = {}
    for target_label, overrides in raw.get("config_overrides", {}).items():
        config_overrides[target_label] = dict(overrides)

    # Filter non-free specs in GPL-only checkout.  Use the `editions` field
    # set by _derive_editions as the source of truth so we catch both
    # "non-free/" and "nonfree/" markers consistently.
    if not is_nonfree_checkout:
        for specs in (install_specs, service_specs):
            specs[:] = [s for s in specs if not s.get("editions")]

    # Sort each list by name for deterministic output
    for specs in (install_specs, service_specs):
        specs.sort(key=lambda s: s["name"])

    return {
        "install_specs": install_specs,
        "service_specs": service_specs,
        "config_overrides": config_overrides,
    }


def _validate_manual_specs(manual: dict[str, Any], repo_root: Path) -> None:
    """Fail if [[service]]/[[package]] entries reference paths that no longer exist."""
    errors: list[str] = []

    for spec in manual.get("service_specs", []):
        name = spec.get("name", "?")
        sp = spec.get("source_prefix", "")
        if sp and not (repo_root / sp.rstrip("/")).is_dir():
            errors.append(f"[[service]] {name}: source_prefix {sp!r} does not exist")
        pt = spec.get("package_target", "")
        if pt and not (repo_root / _label_to_package_path(pt)).is_dir():
            errors.append(f"[[service]] {name}: package_target {pt!r} does not exist")

    for spec in manual.get("install_specs", []):
        name = spec.get("name", "?")
        pt = spec.get("package_target", "")
        if pt and not (repo_root / _label_to_package_path(pt)).is_dir():
            errors.append(f"[[package]] {name}: package_target {pt!r} does not exist")

    if errors:
        raise ValueError(
            "deploy_specs.toml references paths that no longer exist:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# ---------------------------------------------------------------------------
# Auto-discovery: config specs from deps_packages packaging targets
# ---------------------------------------------------------------------------

# Top-level directories of an OMD version tree.  Auto-discovered config
# specs deploy relative to the version root, so every derived site_dest
# must start with one of these.  A dest outside them means the packaging
# target composes its in-archive path from an enclosing pkg_tar
# package_dir, which PackageFilesInfo cannot see -- the deploy would
# land in a directory nothing reads.  Spell the full site-relative path
# out on the pkg_files itself instead (see e624484b8b1 for the pattern).
_VERSION_ROOT_DIRS: frozenset[str] = frozenset({"bin", "include", "lib", "share", "skel"})


def _classify_config_method(source_prefix: str, package_target: str) -> str:
    """Auto-classify a config spec's deploy method from its source path.

    Rules:
    - Targets under active_checks/ with explicit file modes → install_files
    - Targets under locale/ → locale_compile
    - Everything else → copy_dir
    """
    for prefix, method in _CONFIG_METHOD_RULES.items():
        if source_prefix.startswith(prefix + "/") or source_prefix.rstrip("/") == prefix:
            return method
        # Also check the package_target label
        if f"//{prefix}:" in package_target or f"/{prefix}:" in package_target:
            return method
    # Check for notifications (non-template) which use install_files
    if "notifications" in package_target and "templates" not in package_target:
        return "install_files"
    return "copy_dir"


def _discover_config_specs(
    pkg_data: PackagingTargetIndex,
    config_overrides: dict[str, dict[str, Any]],
    _repo_root: Path,
    is_nonfree_checkout: bool,
) -> list[dict[str, Any]]:
    """Auto-discover config specs from packaging targets in the Bazel build graph.

    Uses PackageFilesInfo already queried for all packaging targets to
    auto-derive config specs with source_prefix, site_dest, mode, files,
    and deploy method.

    Config-specific overrides (includes, delete_extra, file_chmod) from the
    TOML are merged in.

    Args:
        pkg_data: PackageFilesInfo index from _cquery_packaging_targets().
        config_overrides: Override map from deploy_specs.toml config_overrides.
        repo_root: Absolute path to the git repository root.
        is_nonfree_checkout: True if repo has non-free/ directory.

    Returns:
        List of config spec dicts, enriched with Bazel-derived data.

    Raises:
        RuntimeError: If a derived site_dest lies outside the version-tree
            roots (deploying it would write to a location nothing reads).
    """
    # We need to identify which packaging targets are config targets
    # (not install targets for compiled artifacts).  Config targets are
    # those referenced by the deps_packages target in omd/BUILD.
    #
    # Since we already have pkg_data from cquery, we use it directly.
    # The install_specs (package targets) are loaded from TOML and handled
    # separately, so any pkg_data target NOT in install_specs is a config target.

    config_specs: list[dict[str, Any]] = []
    dest_violations: list[str] = []

    for target_label, entries in sorted(pkg_data.items()):
        if not entries:
            continue

        # Skip non-free targets in GPL-only checkout
        if not is_nonfree_checkout and "non-free/" in target_label:
            continue

        # Drop entries from external Bazel repos — unpatchable from the local checkout
        editable_entries = [e for e in entries if not _is_external_src(e[2])]
        if not editable_entries:
            logger.debug("Skipping %(target)s: only external sources", {"target": target_label})
            continue

        # Group by source-tree root so heterogeneous targets (e.g. //bin:bin_755,
        # which mixes bin/*.py with cmk/utils/password_store/cli.py) emit one
        # spec per editable source root instead of being skipped wholesale.
        groups = _group_entries_by_source_root(editable_entries)

        # Drop pure-generated, repo-root (no source-tree root), and (in GPL
        # checkout) non-free groups
        groups = [
            (root, gentries)
            for root, gentries in groups
            if root
            and any(is_source for _, _, _, is_source in gentries)
            and (is_nonfree_checkout or root != "non-free")
        ]
        if not groups:
            continue

        target_name = "deploy_" + target_label.lstrip("/").replace("/", "_").replace(":", "_")
        overrides = config_overrides.get(target_label, {})
        includes = overrides.get("includes", [])
        delete_extra = overrides.get("delete_extra", False)
        file_chmod = overrides.get("file_chmod", "")
        services = overrides.get("services", [])
        single_group = len(groups) == 1

        for root, gentries in groups:
            src_paths = [src for _, _, src, _ in gentries]
            dest_paths = [dest for dest, _, _, _ in gentries]
            modes = [mode for _, mode, _, _ in gentries if mode]

            common_src = _common_directory(src_paths)
            common_dest = _common_directory(dest_paths)

            if not common_dest:
                logger.debug(
                    "Skipping %(target)s group %(root)r: no common site_dest",
                    {"target": target_label, "root": root},
                )
                continue

            if common_dest.split("/", 1)[0] not in _VERSION_ROOT_DIRS:
                dest_violations.append(
                    f"  {target_label}: site_dest {common_dest!r}"
                    f" (sources under {common_src or root!r})"
                )
                continue

            files: list[dict[str, Any]] = sorted(
                [
                    {"src": src, "dest": dest, "mode": fmode, "generated": not is_source}
                    for dest, fmode, src, is_source in gentries
                ],
                key=lambda f: f["src"],
            )
            name = target_name if single_group else f"{target_name}__{root}"
            config_specs.append(
                {
                    "delete_extra": delete_extra,
                    "file_chmod": file_chmod,
                    "files": files,
                    "includes": includes,
                    "method": _classify_config_method(common_src, target_label),
                    "mode": int(modes[0], 8) if modes else -1,
                    "name": name,
                    "package_target": target_label,
                    "services": services,
                    "site_dest": common_dest,
                    "source_prefix": common_src,
                }
            )

    if dest_violations:
        roots = ", ".join(sorted(_VERSION_ROOT_DIRS))
        raise RuntimeError(
            "Config spec destinations outside the version tree "
            f"(expected a first path component of: {roots}):\n"
            + "\n".join(dest_violations)
            + "\nSpell out the full site-relative path on the pkg_files "
            'itself (e.g. prefix = "share/check_mk/...").  A path composed '
            "from an enclosing pkg_tar package_dir is invisible to "
            "PackageFilesInfo and would deploy to a location nothing reads "
            "(see e624484b8b1 for the pattern)."
        )

    config_specs.sort(key=lambda s: s["name"])
    return config_specs


def _is_external_src(src: str) -> bool:
    """True if a Bazel source path lives outside the local checkout."""
    return src.startswith(("../", "external/"))


def _common_directory(paths: list[str]) -> str:
    """Return ``commonpath(paths)`` as a directory with trailing slash.

    When ``commonpath`` returns a file (e.g. a single-element group), descend
    to its parent directory so downstream consumers — which assume
    ``source_prefix`` and ``site_dest`` are directory prefixes — can match
    changed-file paths and locate the source on disk.
    """
    if not paths:
        return ""
    common = os.path.commonpath(paths)
    if not common:
        return ""
    if common in paths:
        common = os.path.dirname(common)
    if not common:
        return ""
    return common.rstrip("/") + "/"


def _group_entries_by_source_root(
    entries: list[tuple[str, str, str, bool]],
) -> list[tuple[str, list[tuple[str, str, str, bool]]]]:
    """Group ``(dest, mode, src, is_source)`` entries by the first path component of ``src``.

    Returns a list of ``(root, group_entries)`` tuples sorted by ``root`` for
    deterministic output. Files without a path separator land in a ``""`` root
    group (which the caller filters out alongside other unrootable entries).
    """
    groups: dict[str, list[tuple[str, str, str, bool]]] = {}
    for entry in entries:
        src = entry[2]
        root = src.split("/", 1)[0] if "/" in src else ""
        groups.setdefault(root, []).append(entry)
    return sorted(groups.items())


# ---------------------------------------------------------------------------
# Bazel query helpers
# ---------------------------------------------------------------------------


def _run_bazel_query(
    args: list[str],
    repo_root: Path,
    *,
    timeout: int = _QUERY_TIMEOUT,
) -> subprocess.CompletedProcess[str] | None:
    """Run a bazel command (given without the leading ``bazel``) on the deploy server.

    Returns the result, or ``None`` on timeout/failure.  Accepts exit
    code 3 (partial results with ``--keep_going``).
    """
    try:
        result = subprocess.run(
            bazel_command(args, repo_root),
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "Bazel query timed out after %(timeout)ds for: %(args)s",
            {"timeout": timeout, "args": args},
        )
        return None

    if result.returncode not in (0, 3):
        logger.warning(
            "Bazel query failed (exit %(exit_code)d) for: %(args)s -- %(stderr)s",
            {"exit_code": result.returncode, "args": args, "stderr": result.stderr.strip()},
        )
        return None

    return result


# ---------------------------------------------------------------------------
# Bazel cquery for packaging targets
# ---------------------------------------------------------------------------

# Starlark output formatter for extracting PackageFilesInfo from packaging targets.
# Written to a temp file and passed to ``bazel cquery --output=starlark``.
_STARLARK_PKG_FILES_FORMATTER = """\
_PFINFO = "@@rules_pkg+//pkg:providers.bzl%PackageFilesInfo"

def format(target):
    pfi = providers(target).get(_PFINFO)
    if not pfi:
        return ""
    mode = pfi.attributes.get("mode", "")
    label = "//%s:%s" % (target.label.package, target.label.name)
    lines = []
    for dest, src in pfi.dest_src_map.items():
        lines.append("%s\\t%s\\t%s\\t%s\\t%s" % (
            label,
            dest,
            mode,
            src.short_path,
            src.is_source,
        ))
    return "\\n".join(lines)
"""

# Type alias: label -> [(dest_path, mode_str, src_short_path, is_source)]
PackagingTargetIndex = dict[str, list[tuple[str, str, str, bool]]]


def _cquery_packaging_targets(
    targets: list[str],
    repo_root: Path,
) -> PackagingTargetIndex:
    """Query PackageFilesInfo from specific packaging targets via ``bazel cquery``.

    Writes a temporary Starlark output formatter and runs a single batched
    cquery for all packaging targets.

    Args:
        targets: List of Bazel labels (e.g. ``["//active_checks:active_checks_bin"]``).
        repo_root: Absolute path to the git repository root.

    Returns:
        Dict keyed by target label, mapping to list of
        ``(dest_path, mode_str, src_short_path)`` tuples.
        Empty dict on query failure.
    """
    if not targets:
        return {}

    fd, formatter_path = tempfile.mkstemp(suffix=".cquery.bzl", dir=str(repo_root))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(_STARLARK_PKG_FILES_FORMATTER)

        # Build union expression: target1 + target2 + ...
        union_expr = " + ".join(targets)
        result = subprocess.run(
            bazel_command(
                [
                    "cquery",
                    union_expr,
                    "--output=starlark",
                    f"--starlark:file={formatter_path}",
                ],
                repo_root,
            ),
            capture_output=True,
            text=True,
            check=False,
            cwd=str(repo_root),
            timeout=_QUERY_TIMEOUT * 2,  # cquery is slower than query
        )
    finally:
        os.unlink(formatter_path)

    if result.returncode not in (0, 3):
        raise RuntimeError(
            f"bazel cquery for packaging targets failed (exit {result.returncode}):\n"
            f"{result.stderr.strip()}"
        )

    # Parse output lines: LABEL\tDEST\tMODE\tSRC_SHORT_PATH\tIS_SOURCE
    grouped: PackagingTargetIndex = {}
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        parts = line.split("\t")
        if len(parts) != 5:
            continue
        label, dest, mode, src_path, is_source_str = parts
        grouped.setdefault(label, []).append((dest, mode, src_path, is_source_str == "True"))

    return grouped


def _query_deps_packages_targets(repo_root: Path) -> list[str]:
    """Query all pkg_files targets reachable from //omd:deps_packages.

    Returns a list of target labels for config-type packaging targets.
    """
    # Depth 3 walks into pkg_tar deps (e.g. //bin:pkg_tar) so their pkg_files
    # srcs (//bin:bin_755 etc.) reach the discovery; depth 2 stops at the
    # pkg_tar nodes themselves and silently drops their contents.
    query = 'kind("pkg_files rule", deps(//omd:deps_packages, 3))'
    result = _run_bazel_query(
        ["query", query, "--output=label", "--keep_going"],
        repo_root,
    )
    if result is None:
        output.warn("bazel query for deps_packages failed (see log for details)")
        return []

    targets: list[str] = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line and line.startswith("//"):
            targets.append(line)
    return sorted(targets)


def _query_wheel_prefixes(repo_root: Path) -> list[str]:
    """Derive the source-tree prefixes of deployed wheels from //:deploy-python.

    A plain (non-configured) ``bazel query`` on the ``whls`` attribute unions
    all edition ``select()`` branches, so the result covers every edition.
    The prefix of a wheel is its package directory (e.g. ``//cmk:whl`` ->
    ``cmk/``).
    """
    query = "labels(whls, //:deploy-python_gen)"
    result = _run_bazel_query(
        ["query", query, "--output=label", "--keep_going"],
        repo_root,
    )
    if result is None:
        output.warn("bazel query for deploy-python wheels failed (see log for details)")
        return []

    prefixes = {
        line.strip()[2:].split(":", 1)[0] + "/"
        for line in result.stdout.strip().splitlines()
        if line.strip().startswith("//")
    }
    return sorted(prefixes)


# ---------------------------------------------------------------------------
# Enrichment from packaging targets
# ---------------------------------------------------------------------------


def _label_to_package_path(label: str) -> str:
    """Extract the source package path from a label.

    Strips the ``omd/`` prefix when present, since ``omd/packages/X`` targets
    wrap sources that live in ``packages/X``.

    Examples:
        ``//packages/neb:foo`` → ``packages/neb``
        ``//omd/packages/check-cert:pkg`` → ``packages/check-cert``
    """
    path = label.lstrip("/")
    if ":" in path:
        path = path.split(":")[0]
    if path.startswith("omd/"):
        path = path[len("omd/") :]
    return path


def _enrich_install_specs(
    specs: list[dict[str, Any]],
    pkg_data: PackagingTargetIndex,
) -> None:
    """Derive source_prefix, site_dest, mode, and output_basename from package_target data.

    For each install spec with a package_target, queries the PackageFilesInfo
    entries. For multi-file targets (e.g. cmc helpers), filters by output_basename
    to find the matching entry.

    Modifies *specs* in-place.
    """
    for spec in specs:
        pt = spec.get("package_target", "")
        if not pt:
            continue

        # Derive source_prefix from package_target label if not set
        if not spec.get("source_prefix"):
            spec["source_prefix"] = _label_to_package_path(pt)

        entries = pkg_data.get(pt)
        if not entries:
            logger.warning(
                "No PackageFilesInfo for package_target %(package_target)s (spec %(spec)s)",
                {"package_target": pt, "spec": spec.get("name", "?")},
            )
            continue

        modes = [mode for _, mode, _, _ in entries if mode]

        if len(entries) == 1:
            # Single-file deploy: dest IS the full site_dest path
            dest_path, _, src_path, _ = entries[0]
            if not spec.get("site_dest"):
                spec["site_dest"] = dest_path
            if not spec.get("output_basename"):
                spec["output_basename"] = os.path.basename(src_path)
        else:
            # Multi-file target: find matching entry by output_basename
            output_basename = spec.get("output_basename", "")
            if output_basename:
                for dest, _, src, _ in entries:
                    if (
                        os.path.basename(dest) == output_basename
                        or os.path.basename(src) == output_basename
                    ):
                        if not spec.get("site_dest"):
                            spec["site_dest"] = dest
                        break
            elif not spec.get("site_dest"):
                # No output_basename hint: compute common dest prefix
                common = os.path.commonpath([d for d, _, _, _ in entries])
                if not common.endswith("/"):
                    common += "/"
                spec["site_dest"] = common

        if spec.get("mode", -1) == -1 and modes:
            spec["mode"] = int(modes[0], 8)


def _deploy_name_to_package_path(name: str) -> str:
    """Derive a package path from a deploy target name.

    Strips the ``deploy_wheel_`` prefix and converts underscores to hyphens.

    Example: ``deploy_wheel_cmk_plugins`` → ``packages/cmk-plugins``
    """
    short = name.removeprefix("deploy_wheel_")
    pkg_name = short.replace("_", "-")
    return f"packages/{pkg_name}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_manifest(manifest: dict[str, Any]) -> None:
    """Validate that all required fields are populated after enrichment.

    Raises RuntimeError if any spec has an empty source_prefix or site_dest
    after enrichment.
    """
    unresolved: list[str] = []
    for spec_key in ("config_specs", "install_specs", "service_specs"):
        for spec in manifest.get(spec_key, []):
            if not spec.get("source_prefix", "").strip():
                unresolved.append(
                    f"  {spec_key} '{spec['name']}': empty source_prefix "
                    f"(package_target: {spec.get('package_target', '?')})"
                )
    if unresolved:
        raise RuntimeError(
            "Enrichment failed to resolve source_prefix for the following specs "
            "(empty source_prefix causes downstream git diff failures):\n" + "\n".join(unresolved)
        )

    unresolved_dest: list[str] = []
    for spec in manifest.get("config_specs", []):
        if not spec.get("site_dest", "").strip():
            unresolved_dest.append(
                f"  config_spec '{spec['name']}' "
                f"(source: {spec.get('source_prefix', '?')}, "
                f"package_target: {spec.get('package_target', '?')})"
            )
    for spec in manifest.get("install_specs", []):
        if not spec.get("site_dest", "").strip():
            unresolved_dest.append(
                f"  install_spec '{spec['name']}' "
                f"(source: {spec.get('source_prefix', '?')}, "
                f"package_target: {spec.get('package_target', '?')})"
            )
    if unresolved_dest:
        raise RuntimeError(
            "Enrichment failed to resolve site_dest for the following specs "
            "(deploying with empty site_dest would copy into the site root!):\n"
            + "\n".join(unresolved_dest)
        )


# ---------------------------------------------------------------------------
# Categorization rule computation
# ---------------------------------------------------------------------------


def _query_target_sources(
    install_specs: Collection[Mapping[str, Any]],
    repo_root: Path,
) -> dict[str, frozenset[str]]:
    """Query Bazel for the source files behind each install spec target.

    Runs ``labels(srcs, deps(TARGET))`` once per distinct ``package_target``
    (the first query loads the graph, the rest reuse it) and converts the
    returned labels to repo-relative paths.  Labels from external
    repositories are dropped; targets whose query fails are left out.

    Returns:
        Dict mapping each package_target to the paths of its sources.
    """
    targets = sorted(
        {spec["package_target"] for spec in install_specs if spec.get("package_target")}
    )
    sources: dict[str, frozenset[str]] = {}
    for target in targets:
        result = _run_bazel_query(
            ["query", f"labels(srcs, deps({target}))", "--output=label", "--keep_going"],
            repo_root,
        )
        if result is None:
            logger.warning(
                "Bazel srcs query for %(target)s failed; its sources stay uncategorized",
                {"target": target},
            )
            continue
        sources[target] = frozenset(
            _label_to_source_path(line.strip())
            for line in result.stdout.splitlines()
            if line.strip().startswith("//")
        )
    return sources


def _label_to_source_path(label: str) -> str:
    """``//pkg:sub/file.ext`` -> ``pkg/sub/file.ext``."""
    package, _, name = label[2:].partition(":")
    return f"{package}/{name}" if name else package


def _extension(path: str) -> str | None:
    """Return the file extension of *path* including the dot, or None."""
    basename = path.rsplit("/", 1)[-1]
    return "." + basename.rsplit(".", 1)[-1] if "." in basename else None


def _extensions_by_prefix(
    paths: Collection[str],
    prefixes: Collection[str],
) -> dict[str, frozenset[str]]:
    """Group the file extensions of *paths* by longest matching prefix.

    *prefixes* are directory paths without trailing slash.  Paths under
    none of them and paths without an extension are ignored; prefixes
    that end up without extensions are absent from the result.
    """
    longest_first = sorted(prefixes, key=len, reverse=True)
    grouped: dict[str, set[str]] = {}
    for path in paths:
        if (ext := _extension(path)) is None:
            continue
        if (
            prefix := next((p for p in longest_first if path.startswith(p + "/")), None)
        ) is not None:
            grouped.setdefault(prefix, set()).add(ext)
    return {prefix: frozenset(exts) for prefix, exts in grouped.items()}


_WORKSPACE_PACKAGE_ROOTS: tuple[str, ...] = ("packages/", "non-free/packages/")
"""Directories whose immediate children are workspace packages."""


def _workspace_package(path: str) -> str | None:
    """Return the workspace package directory containing *path*, if any.

    ``packages/cmk-ui-library/lib/x.ts`` -> ``packages/cmk-ui-library``.
    """
    for root in _WORKSPACE_PACKAGE_ROOTS:
        if path.startswith(root):
            name, sep, _rest = path[len(root) :].partition("/")
            return root + name if sep else None
    return None


def _compute_input_prefixes(
    target_sources: Mapping[str, Collection[str]],
    deployable_prefixes: Collection[str],
) -> dict[str, list[str]]:
    """Find the packages each install target is built from that nothing deploys.

    A workspace package can contribute sources to an install target's
    closure without having a wheel, install, or config spec of its own --
    cmk-ui-library feeding the cmk-frontend-vue dist, for instance.
    Changes there reach the site only through the consuming target, so
    its install spec records them as ``input_prefixes``.

    Packages whose sources carry no Bazel-buildable extension (see
    ``_EXTENSION_CATEGORY_PRIORITY``) are skipped: the vue dist's closure
    reaches Python packages through the OpenAPI spec generator, and those
    must keep their Python categorization.

    Args:
        target_sources: Source paths per package_target, as returned by
            :func:`_query_target_sources`.
        deployable_prefixes: Source prefixes (trailing ``/``) that some
            wheel, install, or config spec already deploys.

    Returns:
        Dict mapping package_target to its sorted input prefixes (trailing
        ``/``); targets without input packages are absent.
    """
    deployable = tuple(deployable_prefixes)
    result: dict[str, list[str]] = {}
    for target, paths in target_sources.items():
        candidates = {
            package
            for path in paths
            if (package := _workspace_package(path)) is not None
            and not (package + "/").startswith(deployable)
        }
        extensions = _extensions_by_prefix(paths, candidates)
        prefixes = sorted(
            package + "/"
            for package in candidates
            if _extensions_to_category(extensions.get(package, frozenset())) is not None
        )
        if prefixes:
            result[target] = prefixes
    return result


def _install_spec_extensions(
    install_specs: Collection[Mapping[str, Any]],
    target_sources: Mapping[str, Collection[str]],
) -> dict[str, frozenset[str]]:
    """Source file extensions per install spec prefix, own and input alike.

    Feeds the categorization rules: a prefix's rule matches exactly the
    extensions Bazel reports under it.  Keys carry no trailing slash.
    """
    prefixes = {
        prefix.rstrip("/")
        for spec in install_specs
        for prefix in (spec.get("source_prefix", ""), *spec.get("input_prefixes", []))
        if prefix
    }
    return _extensions_by_prefix(frozenset().union(*target_sources.values()), prefixes)


def _extensions_to_category(
    extensions: frozenset[str],
    *,
    frontend_supervised: bool = False,
) -> ChangeCategory | None:
    """Derive a ChangeCategory from a set of file extensions.

    Uses ``_EXTENSION_CATEGORY_PRIORITY``: the first category whose marker
    extensions intersect with *extensions* wins.

    The ``frontend_supervised`` flag forces VUE regardless of extensions,
    matching the deploy_specs.toml convention for the cmk-frontend-vue package.

    Returns None if no category can be determined.
    """
    if frontend_supervised:
        return ChangeCategory.VUE

    for marker_exts, category in _EXTENSION_CATEGORY_PRIORITY:
        if extensions & marker_exts:
            return category
    return None


def _compute_categorization_rules(
    manifest_data: dict[str, Any],
    install_spec_extensions: dict[str, frozenset[str]],
    supplementary_rules: tuple[CategorizationRule, ...] = (),
) -> list[dict[str, Any]]:
    """Derive categorization rules from manifest specs.

    Produces rules from four sources:
    1. install_specs: compiled artifacts (C++, Rust, Vue, Frontend) with
       extensions derived from the Bazel build graph, for the spec's own
       source_prefix and for its input_prefixes alike
    2. wheel_prefixes: Python packages
    3. config_specs: config/data directories
    4. supplementary_rules: from deploy_specs.toml [[categorization]] entries

    Args:
        manifest_data: The full manifest dict (with enriched specs).
        install_spec_extensions: Mapping of source or input prefix (no
            trailing slash) to frozenset of file extensions, as returned by
            ``_install_spec_extensions``.

    Returns a list of JSON-serializable rule dicts, ordered longest-prefix-first.
    Within the same prefix length, rules with non-null extensions come before
    null-extension rules, then sorted alphabetically by category name.
    """
    seen: set[tuple[str, frozenset[str] | None, str]] = set()
    rules: list[CategorizationRule] = []

    def _add(rule: CategorizationRule) -> None:
        """Add rule if not an exact duplicate."""
        key = (rule.prefix, rule.extensions, rule.category.value)
        if key not in seen:
            seen.add(key)
            rules.append(rule)

    # --- From install_specs (extensions from Bazel build graph) ---
    for spec in manifest_data.get("install_specs", []):
        source_prefix = spec.get("source_prefix", "").rstrip("/")
        if not source_prefix:
            continue

        input_prefixes = (p.rstrip("/") for p in spec.get("input_prefixes", []))
        for prefix in (source_prefix, *input_prefixes):
            extensions = install_spec_extensions.get(prefix, frozenset())
            if not extensions:
                logger.debug(
                    "No source extensions found for install spec %(spec)s (%(prefix)s); skipping",
                    {"spec": spec.get("name", "?"), "prefix": prefix},
                )
                continue

            category = _extensions_to_category(
                extensions,
                frontend_supervised=spec.get("frontend_supervised", False),
            )
            if category is None:
                logger.debug(
                    "Cannot determine category for install spec %(spec)s (%(prefix)s, extensions: %(extensions)s); skipping",
                    {"spec": spec.get("name", "?"), "prefix": prefix, "extensions": extensions},
                )
                continue

            _add(
                CategorizationRule(
                    prefix=prefix + "/",
                    extensions=extensions,
                    category=category,
                )
            )

    # --- From wheel prefixes ---
    for prefix in manifest_data.get("wheel_prefixes", []):
        _add(
            CategorizationRule(
                prefix=prefix,
                extensions=frozenset({".py"}),
                category=ChangeCategory.PYTHON,
            )
        )

    # --- From config_specs ---
    for spec in manifest_data.get("config_specs", []):
        source_prefix = spec.get("source_prefix", "")
        if not source_prefix:
            continue

        # Ensure trailing slash
        if not source_prefix.endswith("/"):
            source_prefix += "/"

        method = spec.get("method", "")
        if method == DeployMethod.LOCALE_COMPILE:
            category = ChangeCategory.DATA
        else:
            category = ChangeCategory.CONFIG

        _add(
            CategorizationRule(
                prefix=source_prefix,
                extensions=None,
                category=category,
            )
        )

    # --- Supplementary rules (from deploy_specs.toml) ---
    for rule in supplementary_rules:
        _add(rule)

    # --- Sort: longest prefix first; within same length, extensions-not-None
    # first, then alphabetically by category name ---
    rules.sort(
        key=lambda r: (
            -len(r.prefix),
            0 if r.extensions is not None else 1,
            r.category.value,
        )
    )

    # Convert to JSON-serializable dicts
    return [
        {
            "prefix": r.prefix,
            "extensions": sorted(r.extensions) if r.extensions is not None else None,
            "category": r.category.value,
        }
        for r in rules
    ]


# ---------------------------------------------------------------------------
# deploy_deps computation
# ---------------------------------------------------------------------------


def _compute_deploy_deps(
    manifest_data: dict[str, Any],
    repo_root: Path,
) -> dict[str, list[str]]:
    """Compute cross-deployer dependency edges from Bazel's dependency graph.

    Uses the ``package_target`` field from deploy specs to identify the Bazel
    target for each source_prefix, then queries Bazel for forward deps to
    build the deploy_deps mapping.

    Deduplicates targets so shared ones (e.g. ``//cmk:cmk_cmk`` for all
    cmk/ prefixes) are only queried once.

    Args:
        manifest_data: Parsed manifest JSON dict (install_specs, config_specs, etc.).
        repo_root: Absolute path to the git repository root.

    Returns:
        Dict mapping source_prefix to sorted list of deployable package deps
        with trailing slashes (e.g. ``{"cmk/gui/": ["packages/cmk-shared-typing/"]}``).
    """
    # 1. Collect all unique source_prefixes and deployable packages
    all_prefixes: set[str] = set()
    deployable_packages: set[str] = set()
    for spec_key in ("install_specs", "config_specs", "service_specs"):
        for spec in manifest_data.get(spec_key, []):
            prefix = spec.get("source_prefix", "")
            if prefix:
                all_prefixes.add(prefix)
                stripped = prefix.rstrip("/")
                if stripped.startswith(("packages/", "non-free/packages/")):
                    deployable_packages.add(stripped)

    # Wheel packages are deployable too (by the wheel step), so install
    # specs depending on them must keep watching their directories.
    for prefix in manifest_data.get("wheel_prefixes", []):
        stripped = prefix.rstrip("/")
        if stripped.startswith(("packages/", "non-free/packages/")):
            deployable_packages.add(stripped)

    if not deployable_packages:
        return {}

    # 2. Build prefix → package_target lookup from all specs (skip empty)
    prefix_to_target: dict[str, str] = {}
    for spec_key in ("install_specs", "config_specs", "service_specs"):
        for spec in manifest_data.get(spec_key, []):
            prefix = spec.get("source_prefix", "")
            pkg_target = spec.get("package_target", "")
            if prefix and pkg_target:
                prefix_to_target.setdefault(prefix, pkg_target)

    # 3. Deduplicate targets and query ALL deps in one batched query
    #    using --output=graph to get per-target edges from DOT format.
    unique_targets = sorted(set(prefix_to_target.values()))
    target_deps_cache: dict[str, set[str]] = {}

    if unique_targets:
        union_expr = " + ".join(unique_targets)
        result = _run_bazel_query(
            [
                "query",
                f"deps({union_expr}, 1)",
                "--output=graph",
                "--keep_going",
            ],
            repo_root,
        )
        if result:
            # Parse DOT edges: "//source" -> "//dep"
            target_set = set(unique_targets)
            for line in result.stdout.splitlines():
                line = line.strip()
                if "->" not in line:
                    continue
                # Format: "//a:b" -> "//c:d"
                parts = line.split("->")
                if len(parts) != 2:
                    continue
                src = parts[0].strip().strip('"')
                dep = parts[1].strip().strip('" ;')
                if src not in target_set:
                    continue
                # Extract package from dep label
                dep_pkg = dep.lstrip("/").split(":")[0]
                if dep_pkg and not dep_pkg.startswith("@"):
                    target_deps_cache.setdefault(src, set()).add(dep_pkg)

        # Filter to deployable packages
        for target in unique_targets:
            raw = target_deps_cache.get(target, set())
            target_deps_cache[target] = raw & deployable_packages

    # 4. Map prefixes to their filtered deps
    deploy_deps: dict[str, list[str]] = {}

    for prefix in sorted(all_prefixes):
        dep_target = prefix_to_target.get(prefix)
        if dep_target is None:
            continue

        filtered = target_deps_cache.get(dep_target, set()).copy()
        # Exclude self-dependency
        filtered.discard(prefix.rstrip("/"))

        if filtered:
            deploy_deps[prefix] = sorted(d + "/" for d in filtered)

    return deploy_deps


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(spinner: Spinner | None = None) -> int:
    """Generate the deploy manifest.

    Args:
        spinner: Optional shared :class:`Spinner` instance.  When provided
            the caller owns the spinner lifecycle (start/stop); this
            function only adds/removes labels.  When ``None`` a local
            spinner is created and managed here.
    """
    import time as _time

    total_start = _time.monotonic()
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent

    is_nonfree_checkout = (repo_root / "non-free").is_dir()

    owns_spinner = spinner is None
    if owns_spinner:
        spinner = Spinner()
        spinner.start()

    def _begin(label: str) -> float:
        assert spinner is not None
        spinner.add_label(label)
        return _time.monotonic()

    def _done(label: str, t0: float, detail: str = "") -> None:
        assert spinner is not None
        elapsed = _time.monotonic() - t0
        spinner.remove_label(label)
        detail_str = f" ({detail})" if detail else ""
        output.info(f"  {label}{detail_str} [{elapsed:.1f}s]")

    def _abort(exc: BaseException) -> int:
        if owns_spinner:
            assert spinner is not None
            spinner.stop()
        output.error(f"Manifest generation failed: {exc}")
        return 1

    output.info("Generating manifest ...")

    # 1. Load manual specs from TOML
    lbl = "Loading TOML specs"
    t0 = _begin(lbl)
    manual = _load_specs_from_toml(specs_path(), is_nonfree_checkout)
    _done(lbl, t0)

    # 2. Auto-discover wheel prefixes and config specs from Bazel
    try:
        lbl = "Querying deploy wheel prefixes"
        t0 = _begin(lbl)
        wheel_prefixes = _query_wheel_prefixes(repo_root)
        _done(lbl, t0, f"{len(wheel_prefixes)} prefixes")

        lbl = "Discovering config targets"
        t0 = _begin(lbl)
        deps_pkg_targets = _query_deps_packages_targets(repo_root)
        _done(lbl, t0, f"{len(deps_pkg_targets)} targets")

        packaging_targets: set[str] = set(deps_pkg_targets)
        for spec in manual.get("install_specs", []):
            pt = spec.get("package_target", "")
            if pt:
                packaging_targets.add(pt)

        lbl = "Querying packaging info"
        t0 = _begin(lbl)
        pkg_data: PackagingTargetIndex = {}
        if packaging_targets:
            pkg_data = _cquery_packaging_targets(sorted(packaging_targets), repo_root)
        _done(lbl, t0, f"{len(packaging_targets)} targets")

        install_targets = {
            spec["package_target"]
            for spec in manual.get("install_specs", [])
            if spec.get("package_target")
        }
        config_pkg_data: PackagingTargetIndex = {
            k: v for k, v in pkg_data.items() if k not in install_targets
        }

        lbl = "Discovering config specs"
        t0 = _begin(lbl)
        config_specs = _discover_config_specs(
            config_pkg_data,
            manual.get("config_overrides", {}),
            repo_root,
            is_nonfree_checkout,
        )
        _done(lbl, t0, f"{len(config_specs)} specs")

        lbl = "Enriching install specs"
        t0 = _begin(lbl)
        _enrich_install_specs(manual.get("install_specs", []), pkg_data)
        _done(lbl, t0)

        # The sources behind the install targets drive categorization (which
        # extensions each prefix owns) and reveal the packages that only reach
        # the site through one of these targets (input_prefixes).
        lbl = "Querying install spec sources"
        t0 = _begin(lbl)
        target_sources = _query_target_sources(manual["install_specs"], repo_root)
        deployable_prefixes = frozenset(wheel_prefixes) | {
            spec["source_prefix"].rstrip("/") + "/"
            for spec in (*manual["install_specs"], *config_specs)
        }
        input_prefixes = _compute_input_prefixes(target_sources, deployable_prefixes)
        for spec in manual["install_specs"]:
            spec["input_prefixes"] = input_prefixes.get(spec["package_target"], [])
        install_spec_extensions = _install_spec_extensions(manual["install_specs"], target_sources)
        _done(
            lbl,
            t0,
            f"{len(target_sources)} targets, "
            f"{sum(len(p) for p in input_prefixes.values())} input packages",
        )

    except Exception as exc:
        return _abort(exc)

    # 3. Merge and validate
    manifest_data: dict[str, Any] = {
        "_version": MANIFEST_VERSION,
        "config_specs": config_specs,
        "install_specs": manual["install_specs"],
        "wheel_prefixes": wheel_prefixes,
        "service_specs": manual["service_specs"],
    }

    try:
        _validate_manifest(manifest_data)
    except RuntimeError as exc:
        return _abort(exc)

    # 3.5 Compute categorization rules from enriched specs + TOML supplementary
    lbl = "Computing categorization rules"
    t0 = _begin(lbl)
    supplementary_rules = _load_supplementary_rules(specs_path())
    categorization_rules = _compute_categorization_rules(
        manifest_data, install_spec_extensions, supplementary_rules
    )
    manifest_data["categorization_rules"] = categorization_rules
    _done(lbl, t0, f"{len(categorization_rules)} rules")

    # 4. Compute deploy_deps
    lbl = "Computing deploy_deps"
    t0 = _begin(lbl)
    computed_deps = _compute_deploy_deps(manifest_data, repo_root)
    manifest_data["deploy_deps"] = computed_deps
    _done(lbl, t0, f"{len(computed_deps)} entries")

    # 5. Write manifest JSON
    dest = repo_root / MANIFEST_REPO_PATH
    with open(dest, "w") as f:
        json.dump(manifest_data, f, indent=2, sort_keys=True)
        f.write("\n")

    # 6. Save per-file hashes for staleness detection
    save_manifest_hashes(repo_root)

    if owns_spinner:
        assert spinner is not None
        spinner.stop()

    n_specs = sum(len(manifest_data[k]) for k in ("config_specs", "install_specs", "service_specs"))
    total_elapsed = _time.monotonic() - total_start
    output.info(
        f"Manifest generated in {total_elapsed:.1f}s ({n_specs} specs, {len(computed_deps)} deps)"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
