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

import logging
from dataclasses import dataclass, field
from pathlib import Path

from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk as _cmk_integration
from cmk.maps.shared.config_vars import VAR_FOLDER_HIDE_UNREADABLE, VAR_FOLDER_PERMS

log = logging.getLogger(__name__)


def _folder_perms_path() -> Path:
    return (
        Path(settings.checkmk_omd_root) / "etc" / "check_mk" / "maps.d" / "wato" / "folder_perms.mk"
    )


def folder_perms_mtime() -> float:
    """Return mtime of the folder-perms file for cache invalidation, or 0.0 when absent."""
    return _cmk_integration.mtime_or_zero(_folder_perms_path())


@dataclass(frozen=True)
class FolderSkeleton:
    """Each folder carries ``path``, ``title``, ``folder_id`` and the effective
    ``permitted_groups`` — the shape the GUI writer produces."""

    folders: list[dict[str, object]] = field(default_factory=list)
    # Setup's ``wato_hide_folders_without_read_permissions``.
    hide_unreadable: bool = False


def load_folder_perms() -> FolderSkeleton:
    """Return the prepared folder skeleton, empty when the file is missing,
    unparseable or empty."""
    p = _folder_perms_path()
    if not p.is_file():
        return FolderSkeleton()
    try:
        values = _cmk_integration.exec_mk_file(
            p, {VAR_FOLDER_PERMS: [], VAR_FOLDER_HIDE_UNREADABLE: False}
        )
    except Exception:
        log.exception("Failed to parse %(path)s", {"path": p})
        return FolderSkeleton()
    raw = values[VAR_FOLDER_PERMS]
    return FolderSkeleton(
        [dict(entry) for entry in raw if isinstance(entry, dict)] if isinstance(raw, list) else [],
        values[VAR_FOLDER_HIDE_UNREADABLE] is True,
    )
