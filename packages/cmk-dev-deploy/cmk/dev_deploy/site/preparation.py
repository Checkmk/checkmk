# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Backend seam for making an OMD site writable before deploys.

Deployers write through ``site.root/...`` paths; a *site preparation
backend* makes those paths writable for the deploy user.  The default
backend mounts an OverlayFS over the site root (:mod:`overlay`).  The
seam exists so the experimental clone backend (a writable per-site copy
of the OMD version directory) can be selected with ``--backend`` without
touching the overlay path.

The backend used for a site is recorded in the deploy state, so
subsequent runs and ``--purge`` dispatch to the backend that actually
prepared the site.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import ClassVar, Protocol

from cmk.dev_deploy.core import output
from cmk.dev_deploy.errors import DeployError
from cmk.dev_deploy.site import sudoers
from cmk.dev_deploy.site.overlay import ensure_overlay, is_overlay_active, teardown_overlay
from cmk.dev_deploy.site.privilege import ensure_sudo, SSHState
from cmk.dev_deploy.site.version_clone import ensure_clone, is_clone_active, teardown_clone

DEFAULT_BACKEND = "overlay"


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
class OverlayBackend:
    """Default backend: OverlayFS mount over the site root (see overlay.py)."""

    ssh_state: SSHState
    name: ClassVar[str] = "overlay"

    def is_active(self, site_root: Path) -> bool:
        return is_overlay_active(site_root)

    def prepare_privileges(self, site_root: Path, *, full: bool) -> None:
        # Pre-authenticate sudo early -- before the manifest rebuild which
        # can take minutes and would otherwise expire the sudo timestamp.
        if full or not is_overlay_active(site_root):
            output.info("Overlay setup requires sudo privileges")
            ensure_sudo()

    def ensure(self, site_root: Path) -> None:
        ensure_overlay(site_root, self.ssh_state)

    def teardown(self, site_root: Path) -> None:
        # --purge reaches teardown without prepare_privileges; refreshing a
        # cached sudo timestamp is free, so always pre-authenticate here.
        ensure_sudo()
        teardown_overlay(site_root)


@dataclasses.dataclass(frozen=True)
class CloneBackend:
    """Experimental backend: writable per-site clone of the version directory."""

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


def resolve_backend_name(explicit: str | None, recorded: str, site_root: Path) -> str:
    """Pick the backend: explicit flag > state record > detection > default.

    Detection covers lost deploy state (e.g. after ``--full`` was
    interrupted): a site whose ``version`` symlink points at a clone must
    keep dispatching to the clone backend.
    """
    if explicit:
        return explicit
    if recorded:
        return recorded
    if is_clone_active(site_root):
        return CloneBackend.name
    return DEFAULT_BACKEND


def create_backend(name: str, ssh_state: SSHState) -> SitePreparation:
    """Instantiate the named site preparation backend."""
    if name == OverlayBackend.name:
        return OverlayBackend(ssh_state)
    if name == CloneBackend.name:
        return CloneBackend()
    raise DeployError(f"Unknown site preparation backend: {name!r}")


def check_backend_conflict(name: str, site_root: Path) -> str | None:
    """Refuse to mix backends on one site; returns an error message or None."""
    if name != OverlayBackend.name and is_overlay_active(site_root):
        return (
            f"An OverlayFS is mounted on {site_root}; refusing to use the {name} backend.\n"
            "  Purge the overlay first: cmk-dev-deploy --purge --backend overlay"
        )
    if name != CloneBackend.name and is_clone_active(site_root):
        return (
            f"The version symlink of {site_root} points at a clone; "
            f"refusing to use the {name} backend.\n"
            "  Purge the clone first: cmk-dev-deploy --purge --backend clone"
        )
    return None
