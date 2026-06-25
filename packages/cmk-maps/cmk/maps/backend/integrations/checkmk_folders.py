#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Read the prepared SETUP-folder skeleton for the folder-tree map.

Resolving folder titles/ids and the effective read-permitted contact groups
(own + inherited via ``recurse_perms``) is watolib logic. The GUI
(``cmk.maps.gui._folders``) resolves it with the real ``Folder.groups()`` on
every activation and writes the ready-to-use skeleton to
``etc/check_mk/maps.d/wato/folder_perms.mk`` (shipped to remotes by the Maps
ReplicationPath). This module only reads it back — the daemon does the trivial
per-user scope match itself (``FolderScope`` in :mod:`checkmk`).

Flask-free, the same direct ``exec`` pattern :mod:`checkmk_sites` uses. A missing
or empty file means "no folder skeleton yet" (fresh site before the first
activation): the folder-tree map then shows only folders that contain hosts,
resolved from Livestatus alone.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk as _cmk_integration
from cmk.maps.shared.config_vars import VAR_FOLDER_PERMS

log = logging.getLogger(__name__)


def _folder_perms_path() -> Path:
    return (
        Path(settings.checkmk_omd_root) / "etc" / "check_mk" / "maps.d" / "wato" / "folder_perms.mk"
    )


def folder_perms_mtime() -> float:
    """Return mtime of the folder-perms file for cache invalidation, or 0.0 when absent."""
    return _cmk_integration.mtime_or_zero(_folder_perms_path())


def load_folder_perms() -> list[dict[str, object]]:
    """Return the prepared folder skeleton, or ``[]`` when the file is missing,
    unparseable or empty.

    Each entry carries ``path``, ``title``, ``folder_id`` and the effective
    ``permitted_groups`` — the shape the GUI writer produces.
    """
    p = _folder_perms_path()
    if not p.is_file():
        return []
    try:
        raw = _cmk_integration.exec_mk_file(p, {VAR_FOLDER_PERMS: []})[VAR_FOLDER_PERMS]
    except Exception:
        log.exception("Failed to parse %(path)s", {"path": p})
        return []
    if not isinstance(raw, list):
        return []
    return [dict(entry) for entry in raw if isinstance(entry, dict)]
