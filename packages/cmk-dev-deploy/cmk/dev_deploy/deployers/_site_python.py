# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared site-Python discovery utilities for deployers.

Cached sysconfig-based path discovery for the OMD site's Python interpreter,
with glob and legacy fallbacks when ``bin/python3`` is missing.
"""

from __future__ import annotations

import functools
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.subprocess_utils import run_checked
from cmk.dev_deploy.errors import DeployError
from cmk.dev_deploy.types import SiteInfo

_SYSCONFIG_TIMEOUT: int = 10


def get_site_packages(site: SiteInfo) -> Path:
    """Discover the site-packages path for an OMD site's Python (cached)."""
    return _discover_site_packages_cached(str(site.root))


@functools.lru_cache(maxsize=8)
def _discover_site_packages_cached(site_root_str: str) -> Path:
    """Cached implementation keyed on string (Path is not hashable)."""
    site_root = Path(site_root_str)
    python = site_root / "bin" / "python3"
    if python.exists():
        return _discover_purelib(python)

    lib_dir = _glob_python_lib_dir(site_root)
    if lib_dir is None:
        raise DeployError(
            f"Cannot discover site-packages: no bin/python3 and no lib/python3.*/ "
            f"found under {site_root}",
            recovery="Ensure the OMD site is properly set up.",
        )
    return lib_dir / "site-packages"


def _glob_python_lib_dir(site_root: Path) -> Path | None:
    """Glob for ``lib/python3.*/`` under the site root, picking the highest version."""
    candidates = sorted(site_root.glob("lib/python3.*/"))
    if not candidates:
        return None
    if len(candidates) > 1:
        output.warn(f"Multiple Python lib dirs found: {candidates}, using {candidates[-1]}")
    return candidates[-1]


def _discover_purelib(site_python: Path) -> Path:
    """Run sysconfig discovery via the site's Python interpreter."""
    return Path(
        run_checked(
            [
                str(site_python),
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
            ],
            cwd=site_python.parent,
            timeout=_SYSCONFIG_TIMEOUT,
            description="sysconfig discovery",
            recovery="Check that the site Python environment is functional.",
        ).stdout.strip()
    )
