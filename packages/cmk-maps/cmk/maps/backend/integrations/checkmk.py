#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ``exec_mk_file`` hands back a raw ``exec`` namespace; ``exec``'s globals
# parameter is typed ``dict[str, Any]``, so the namespace cannot be narrowed here.
# mypy: disable-error-code="explicit-any"
"""
Checkmk Python integration for the Maps daemon.

Exposes the bits of Checkmk the daemon needs without a GUI request context:
the SETUP folder-scope derived from a ticket Principal, the monitoring core,
and ``.mk`` file reading. The daemon runs under the site interpreter
(``bin/gunicorn``), so its dependencies resolve through the regular
site-packages — no ``sys.path`` tinkering.

Authorization is NOT done here: the GUI bakes every permission decision into
the signed ticket (see ``cmk.maps.backend.core.auth.Principal``), so the
daemon never reads ``roles.mk`` / ``users.mk`` itself.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.core.config import settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FolderScope:
    """A user's SETUP-folder *read* visibility (distinct from monitoring host
    visibility / Livestatus AuthUser).

    Checkmk gates folder reads on ``wato.see_all_folders`` (admin-only) OR
    membership in a folder's contact groups — NOT on ``general.see_all`` (which
    a guest has). So a see-all guest sees every monitored host but must not see
    SETUP folder names outside their contact groups.

    ``see_all`` → may read every folder. Otherwise a folder is readable iff its
    effective contact groups intersect ``groups``. ``key`` is a stable hashable
    identity so subscribers/snapshots with the same folder visibility share work.
    """

    see_all: bool
    groups: frozenset[str] = frozenset()

    @property
    def key(self) -> str:
        return "*" if self.see_all else "cg:" + ",".join(sorted(self.groups))

    def permits(self, permitted_groups: Iterable[str]) -> bool:
        return self.see_all or bool(self.groups & set(permitted_groups))


def mtime_or_zero(path: Path) -> float:
    """Return *path*'s mtime for cache invalidation, or 0.0 when absent/unreadable."""
    try:
        return path.stat().st_mtime if path.is_file() else 0.0
    except OSError:
        return 0.0


def exec_mk_file(path: Path, defaults: dict[str, Any]) -> dict[str, Any]:
    """Exec a Checkmk ``.mk`` config file and return its variable namespace.

    Threat model: ``.mk`` files are owned by the OMD site user we run as, so
    ``exec`` introduces no additional privilege boundary. Do not loosen this
    file-ownership expectation without re-auditing all callers.
    """
    ns: dict[str, Any] = dict(defaults)
    if path.is_file():
        exec(compile(path.read_bytes(), str(path), "exec"), ns)  # nosec B102 # BNS:aee528
    return ns


MonitoringCore = Literal["cmc", "nagios"]


def get_monitoring_core() -> MonitoringCore | None:
    """Return 'cmc', 'nagios', or None (not in OMD or file unreadable).

    Reads CONFIG_CORE from $OMD_ROOT/etc/omd/site.conf.
    Never raises; fails safe (returns None) so callers can show all UI fields.
    """
    site_conf = Path(settings.checkmk_omd_root) / "etc" / "omd" / "site.conf"
    try:
        text = site_conf.read_text(encoding="utf-8")
    except OSError as exc:
        log.debug(
            "get_monitoring_core: cannot read %(site_conf)s: %(error)s",
            {"site_conf": site_conf, "error": exc},
        )
        return None
    for line in text.splitlines():
        if line.strip().startswith("CONFIG_CORE="):
            value = line.split("=", 1)[1].strip().strip("'\"")
            if value in ("cmc", "nagios"):
                return value  # type: ignore[return-value]
            return None
    log.debug(
        "get_monitoring_core: CONFIG_CORE not found in %(site_conf)s",
        {"site_conf": site_conf},
    )
    return None


def resolve_folder_scope(principal: Principal) -> FolderScope:
    """The SETUP-folder read visibility for a principal (see :class:`FolderScope`).

    Derived purely from the capabilities the GUI baked into the ticket
    (``wato.see_all_folders`` → ``folder_see_all`` and the user's contact
    groups); the daemon performs no Checkmk user-DB lookup of its own.
    """
    if principal.folder_see_all:
        return FolderScope(see_all=True)
    return FolderScope(see_all=False, groups=principal.contact_groups)
