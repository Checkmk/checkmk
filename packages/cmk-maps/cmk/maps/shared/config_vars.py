#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI↔daemon ``.mk``-file variable names for the Maps daemon's prepared config.

The Maps daemon has no GUI/RBAC context, so the GUI writes the daemon's runtime
config, prepared Livestatus site specs and SETUP-folder skeleton to ``.mk`` files
under ``maps.d/`` and the daemon reads them back. Both sides name the file
variables from here so the on-disk contract can't drift by a stray string edit;
the file *shapes* are pinned separately by the ``test_*_contract`` tests.

Written by ``cmk.maps.gui`` (``_config_domain`` / ``_sites`` / ``_folders``), read
by ``cmk.maps.backend.integrations`` (``checkmk_globals`` / ``checkmk_sites`` /
``checkmk_folders``). GUI-only authoring defaults (``maps_map_defaults`` etc.) are
never read by the daemon and stay GUI-side.
"""

from typing import TypedDict

# Runtime global settings — ConfigDomainMaps' global.mk / sitespecific.mk.
VAR_CONNECTIONS = "maps_connections"
VAR_LOG_LEVEL = "maps_log_level"
VAR_STATE_REFRESH_INTERVAL = "maps_state_refresh_interval"

# Prepared Livestatus site specs — maps.d/sitespecs.mk.
VAR_SITE_SPECS = "maps_site_specs"

# Prepared SETUP-folder skeleton — maps.d/wato/folder_perms.mk.
VAR_FOLDER_PERMS = "maps_folder_perms"


class FolderPermEntry(TypedDict):
    """One SETUP folder in the prepared skeleton stored under ``VAR_FOLDER_PERMS``.

    ``permitted_groups`` is the effective *read* permission (the folder's own
    contact groups plus those inherited from any ancestor with ``recurse_perms``),
    resolved GUI-side via the real ``Folder.groups()``. It is user-independent, so
    one file serves every viewer; the daemon only does the per-user scope match.
    """

    path: str
    title: str
    folder_id: str
    permitted_groups: list[str]
