# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Backend seam for making an OMD site writable before deploys.

Deployers write through ``site.root/...`` paths; a *site preparation
backend* makes those paths writable for the deploy user.  The only
backend is the clone backend (a writable per-site copy of the OMD
version directory, see :mod:`version_clone`); the seam remains so other
strategies can be added without touching the orchestration.

The OverlayFS backend that preceded the clone has been removed.  A
leftover overlay mount or deploy state from an older cmk-dev-deploy is
detected and refused with manual recovery instructions.
"""

import dataclasses
from pathlib import Path
from typing import ClassVar, Protocol

from cmk.dev_deploy.errors import DeployError
from cmk.dev_deploy.site import sudoers
from cmk.dev_deploy.site.version_clone import ensure_clone, is_clone_active, teardown_clone

DEFAULT_BACKEND = "clone"


class SitePreparation(Protocol):
    """How a site is made writable for deploys."""

    @property
    def name(self) -> str: ...

    def is_active(self, site_root: Path) -> bool:
        """Whether the site is currently prepared by this backend."""

    def prepare_privileges(self, site_root: Path, *, full: bool) -> None:
        """Acquire the credentials :func:`ensure`/:func:`teardown` will need.

        Runs before potentially slow steps (manifest rebuild) so that any
        interactive prompt happens immediately at startup.
        """

    def ensure(self, site_root: Path) -> None:
        """Prepare the site for deploys (idempotent)."""

    def teardown(self, site_root: Path) -> None:
        """Revert the site to its pristine state, leaving it stopped."""


@dataclasses.dataclass(frozen=True)
class CloneBackend:
    """Writable per-site clone of the version directory (see version_clone.py)."""

    name: ClassVar[str] = "clone"

    def is_active(self, site_root: Path) -> bool:
        return is_clone_active(site_root)

    def prepare_privileges(self, site_root: Path, *, full: bool) -> None:  # noqa: ARG002
        # The probe runs on every invocation, independent of --full.
        if not sudoers.probe(site_root.name):
            sudoers.bootstrap(site_root.name)
        sudoers.ensure_dev_versions_dir()

    def ensure(self, site_root: Path) -> None:
        ensure_clone(site_root)

    def teardown(self, site_root: Path) -> None:
        teardown_clone(site_root)


def resolve_backend_name(recorded: str, site_root: Path) -> str:
    """Pick the backend: deploy-state record > active-backend detection > default."""
    if recorded:
        return recorded
    if is_clone_active(site_root):
        return CloneBackend.name
    return DEFAULT_BACKEND


def create_backend(name: str) -> SitePreparation:
    """Instantiate the named site preparation backend."""
    if name == CloneBackend.name:
        return CloneBackend()
    if name == "overlay":
        raise DeployError(
            "This site was prepared by the OverlayFS backend, which has been removed.",
            recovery=(
                "Revert the site manually:\n"
                "  sudo umount /omd/sites/<site>    (if still mounted)\n"
                "  sudo rm -rf /var/tmp/cmk-dev-deploy/<site>\n"
                "or purge it with an older cmk-dev-deploy version, then deploy again."
            ),
        )
    raise DeployError(f"Unknown site preparation backend: {name!r}")


def check_backend_conflict(site_root: Path) -> str | None:
    """Refuse to prepare a site that still carries an old overlay mount."""
    if _overlay_mounted(site_root):
        return (
            f"An OverlayFS (from a previous cmk-dev-deploy version) is mounted on "
            f"{site_root}; refusing to prepare the site.\n"
            f"  Revert it first: sudo umount {site_root} "
            f"&& sudo rm -rf /var/tmp/cmk-dev-deploy/{site_root.name}"
        )
    return None


def _overlay_mounted(site_root: Path) -> bool:
    """Detect a leftover OverlayFS mount on the site root via /proc/mounts."""
    try:
        mounts = Path("/proc/mounts").read_text()
    except OSError:
        return False
    resolved = str(site_root.resolve())
    return any(
        len(parts := line.split()) >= 3 and parts[0] == "overlay" and parts[1] == resolved
        for line in mounts.splitlines()
    )
