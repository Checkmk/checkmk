# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Site detection and validation for cmk-dev-deploy."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.errors import RepoNotFoundError, SiteError, SiteNotFoundError
from cmk.dev_deploy.types import Edition, SiteInfo


def find_repo_root() -> Path:
    """Find the git repository root via BUILD_WORKSPACE_DIRECTORY or git."""
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir:
        root = Path(workspace_dir)
        os.chdir(root)
        return root

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RepoNotFoundError(
            "Not inside a git repository",
            recovery="Run cmk-dev-deploy from within the Checkmk source tree.",
        )
    return Path(result.stdout.strip())


def find_site_root(site_name: str | None) -> Path | None:
    """Return the site root path without full validation, or None."""
    if site_name is None:
        return None
    site_root = Path("/omd/sites") / site_name
    if site_root.exists():
        return site_root
    # Site dir gone but overlay data may still exist — return the path
    # so teardown_overlay can clean up.
    overlay_dir = Path("/var/tmp/cmk-dev-deploy") / site_name  # nosec B108
    if overlay_dir.exists():
        return site_root
    return None


def resolve_site(cli_site: str | None, repo_root: Path, cwd: Path) -> SiteInfo:
    """Resolve and validate an OMD site, returning full SiteInfo."""
    site_name = _resolve_site_name(cli_site, repo_root, cwd)
    site_root = Path("/omd/sites") / site_name

    if not site_root.is_dir():
        available = _list_sites()
        raise SiteNotFoundError(
            f"Site directory does not exist: {site_root}",
            recovery=(
                f"Available sites: {available}\nCreate with: omd create {site_name}"
            ),
        )

    edition, version_string = _read_edition(site_root)
    build_commit = read_build_commit(site_root)

    return SiteInfo(
        name=site_name,
        root=site_root,
        edition=edition,
        version_string=version_string,
        build_commit=build_commit,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_site_name(cli_site: str | None, repo_root: Path, cwd: Path) -> str:
    """Resolve site name: CLI > .site file > SITE env > omd sites."""
    # 1. Explicit CLI argument
    if cli_site is not None:
        return cli_site

    # 2. .site file at repo root
    site_name = _read_site_file(repo_root / ".site")
    if site_name is not None:
        return site_name

    # 3. Walk up from cwd (only if cwd is NOT under repo_root, since we
    #    already checked repo_root above)
    if not _is_subpath(cwd, repo_root):
        site_name = _walk_up_for_site_file(cwd)
        if site_name is not None:
            return site_name

    # 4. SITE environment variable (deprecated fallback for .f12 migration)
    env_site = os.environ.get("SITE")
    if env_site:
        output.warn(
            f"Using SITE environment variable ({env_site!r}). "
            "Consider using --site flag or .site file instead."
        )
        return env_site

    # 5. Fall back to omd sites --bare
    return _resolve_from_omd(repo_root)


def _read_site_file(path: Path) -> str | None:
    """Read a .site file and return the first non-comment line, or None."""
    if not path.is_file():
        return None

    try:
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
    except OSError:
        return None

    return None


def _walk_up_for_site_file(start: Path) -> str | None:
    """Walk up from *start* to filesystem root looking for a .site file."""
    current = start.resolve()
    while True:
        site_name = _read_site_file(current / ".site")
        if site_name is not None:
            return site_name
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _is_subpath(child: Path, parent: Path) -> bool:
    """Return True if *child* is equal to or a descendant of *parent*."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_from_omd(repo_root: Path) -> str:
    """Fall back to ``omd sites --bare``; auto-select if exactly one site."""
    result = subprocess.run(
        ["omd", "sites", "--bare"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        raise SiteNotFoundError(
            "No OMD site found",
            recovery=(
                "To fix this, either:\n"
                f"  1. Create a .site file: echo 'SITENAME' > {repo_root / '.site'}\n"
                "  2. Specify site explicitly: cmk-dev-deploy --site SITENAME\n"
                "  3. Create an OMD site: omd create SITENAME"
            ),
        )

    sites = [s for s in result.stdout.strip().splitlines() if s.strip()]

    if len(sites) == 1:
        return sites[0].strip()

    site_list = ", ".join(sites)
    raise SiteNotFoundError(
        f"Multiple OMD sites found: {site_list}",
        recovery=(
            "Specify which site:\n"
            "  cmk-dev-deploy --site SITENAME\n"
            f"  echo 'SITENAME' > {repo_root / '.site'}"
        ),
    )


def _read_edition(site_root: Path) -> tuple[Edition, str]:
    """Read the site edition and version string from the version symlink."""
    version_link = site_root / "version"

    if not version_link.exists():
        raise SiteError(
            f"No version symlink at {version_link}",
            recovery=f"Site may be corrupted. Try: omd update {site_root.name}",
        )

    target = os.readlink(version_link)
    version_dir = Path(target).name  # e.g. "2.6.0-2026.02.13.pro"
    suffix = version_dir.rsplit(".", 1)[-1]  # e.g. "pro"

    try:
        edition = Edition.from_version_suffix(suffix)
    except ValueError:
        valid = ", ".join(e.value for e in Edition)
        raise SiteError(
            f"Unknown edition suffix '{suffix}' in version: {version_dir}",
            recovery=(
                f"Expected one of: {valid}\n"
                "If this is an older site (pre-2.6.0), rebuild it with a 2.6.0+ daily build."
            ),
        )

    return edition, version_dir


def read_build_commit(site_root: Path) -> str | None:
    """Read the 40-char git commit hash from the site's COMMIT file, or None."""
    commit_file = site_root / "share" / "doc" / "COMMIT"

    if not commit_file.is_file():
        return None

    try:
        commit = commit_file.read_text().strip()
    except OSError:
        return None

    if len(commit) != 40 or not all(c in "0123456789abcdef" for c in commit):
        return None

    return commit


def _list_sites() -> str:
    """Return a comma-separated list of available OMD sites, or a fallback string."""
    result = subprocess.run(
        ["omd", "sites", "--bare"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return ", ".join(
            s.strip() for s in result.stdout.strip().splitlines() if s.strip()
        )
    return "(none found)"
