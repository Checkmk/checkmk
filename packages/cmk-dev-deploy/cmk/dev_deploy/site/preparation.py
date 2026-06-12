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
from cmk.dev_deploy.site.overlay import ensure_overlay, is_overlay_active, teardown_overlay
from cmk.dev_deploy.site.privilege import ensure_sudo, SSHState

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


def resolve_backend_name(explicit: str | None, recorded: str) -> str:
    """Pick the backend: explicit flag > deploy-state record > default."""
    return explicit or recorded or DEFAULT_BACKEND


def create_backend(name: str, ssh_state: SSHState) -> SitePreparation:
    """Instantiate the named site preparation backend."""
    if name == "overlay":
        return OverlayBackend(ssh_state)
    raise DeployError(f"Unknown site preparation backend: {name!r}")
