# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Wheel deployment via ``bazel run //:deploy-python``.

Bazel builds the edition's ``py_wheel`` targets and uv force-reinstalls
them against the site Python, including bytecode compilation. The wheel
lists in ``bazel/rules/deploy.bzl`` are the single source of truth for
what gets deployed; this module only decides *whether* the step needs to
run. Unchanged wheels are no-ops for Bazel's action cache, and the
reinstall itself takes a few seconds, so there is no per-package
selection.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.subprocess_utils import run_checked
from cmk.dev_deploy.core.timeouts import BAZEL_BUILD
from cmk.dev_deploy.errors import WheelDeployError
from cmk.dev_deploy.manifest.reader import get_wheel_prefixes
from cmk.dev_deploy.site.sudoers import DEV_VERSIONS_DIR
from cmk.dev_deploy.types import ChangeSet, SiteInfo, WheelDeployResult

DEPLOY_PYTHON_TARGET = "//:deploy-python"


def wheel_prefixes() -> tuple[str, ...]:
    """Source-tree prefixes covered by wheel deployment."""
    return get_wheel_prefixes()


def has_wheel_changes(changes: ChangeSet | None) -> bool:
    """Return True when any changed or deleted file belongs to a deployed wheel.

    ``None`` means "no change detection baseline": deploy everything.
    Deleted files matter too -- the wheel containing them must be
    reinstalled so pip removes them from the site.
    """
    if changes is None:
        return True
    prefixes = wheel_prefixes()
    return any(f.startswith(prefixes) for f in changes.files + changes.deleted_files)


def _check_site_layout(site: SiteInfo) -> None:
    """Reject sites predating the standard site-packages layout.

    Old site builds keep their Python code in ``lib/python3``, which
    shadows anything pip installs into ``lib/python3.XY/site-packages``.
    """
    legacy = site.root / "lib" / "python3"
    if legacy.is_dir() and not legacy.is_symlink():
        raise WheelDeployError(
            f"Site '{site.name}' uses the legacy lib/python3 layout",
            recovery="Rebuild the site from a current master build; wheel "
            "deployment only supports the standard site-packages layout.",
        )


def _uv_cache_env() -> dict[str, str] | None:
    """Environment placing the uv cache on the site's filesystem.

    uv installs wheels via hardlinks when its cache shares a filesystem
    with the target site-packages; the default ``~/.cache/uv`` usually
    does not share one with ``/omd``, forcing full copies of every file.
    The clone base directory is deploy-user-owned and guaranteed to be
    on the site's filesystem.  Returns ``None`` (inherit the unchanged
    environment) when the user already configured a cache or the clone
    base does not exist.
    """
    if "UV_CACHE_DIR" in os.environ or not os.access(DEV_VERSIONS_DIR, os.W_OK):
        return None
    return {**os.environ, "UV_CACHE_DIR": str(DEV_VERSIONS_DIR / ".uv-cache")}


def deploy_wheels(repo_root: Path, site: SiteInfo) -> WheelDeployResult:
    """Build and force-reinstall all of the edition's wheels into the site."""
    start = time.monotonic()
    _check_site_layout(site)

    result = run_checked(
        [
            "bazel",
            "run",
            "--noshow_progress",
            DEPLOY_PYTHON_TARGET,
            f"--cmk_edition={site.edition.value}",
            "--",
            str(site.root),
        ],
        cwd=repo_root,
        timeout=BAZEL_BUILD,
        env=_uv_cache_env(),
        error_cls=WheelDeployError,
        description=f"bazel run {DEPLOY_PYTHON_TARGET}",
        recovery=f"Check 'bazel run {DEPLOY_PYTHON_TARGET} "
        f"--cmk_edition={site.edition.value} -- {site.root}' manually.",
    )

    # uv reports one " + name==version" (installed) or " ~ name==version"
    # (reinstalled) line per wheel on stderr.
    install_lines = [line for line in result.stderr.splitlines() if line.startswith((" + ", " ~ "))]
    for line in install_lines:
        output.verbose(f" {line}")

    return WheelDeployResult(
        wheels_installed=len(install_lines),
        elapsed=time.monotonic() - start,
    )
