#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Prepared SETUP-folder skeleton for the Maps daemon's folder-tree map.

A folder-tree map bubbles live host/service states up the SETUP folder
hierarchy, scoped to the folders the viewing user may *read*. Resolving that
hierarchy — folder titles, ids, and the effective read-permitted contact groups
(a folder's own groups plus those inherited from any ancestor whose
``recurse_perms`` is set) — is ``cmk.gui.watolib`` logic. Rather than have the
daemon re-implement ``Folder.groups()`` off the raw ``.wato`` files, the GUI
resolves it with the *real* watolib on every activation and writes the
ready-to-use skeleton to ``etc/check_mk/maps.d/wato/folder_perms.mk``, shipped to
remote sites by the Maps ReplicationPath — the same prepared-file pattern
:mod:`cmk.maps.gui._sites` uses for the Livestatus site specs.

The daemon reads it back (``cmk.maps.backend.integrations.checkmk_folders``) and
only does the trivial per-user scope match; ``permitted_groups`` is
user-independent, so one file serves every viewer. Resolving on
``pre-activate-changes`` (like mkeventd regenerates its config) lands the file in
the same activation's replication snapshot.
"""

from pathlib import Path

import cmk.utils.paths
from cmk.ccc import store
from cmk.gui import hooks
from cmk.gui.log import logger
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.maps.shared.config_vars import FolderPermEntry, VAR_FOLDER_PERMS


def folder_perms_path() -> Path:
    return cmk.utils.paths.default_config_dir / "maps.d" / "wato" / "folder_perms.mk"


def _resolve_folder_skeleton() -> list[FolderPermEntry]:
    """Every SETUP folder with its title, stable id and effective read-permitted
    contact groups, resolved via the real ``Folder.groups()``.

    ``groups()`` returns ``(permitted_groups, host_contact_groups, ...)``; the
    daemon only needs the first — the effective *read* permission incl. the
    ``recurse_perms`` ancestor inheritance.
    """
    tree = folder_tree()
    skeleton: list[FolderPermEntry] = []
    for folder in tree.all_folders().values():
        permitted_groups, _host_contact_groups, _use_for_services = folder.groups()
        skeleton.append(
            FolderPermEntry(
                path=folder.path(),
                title=folder.title(),
                folder_id=folder.id(),
                permitted_groups=sorted(permitted_groups),
            )
        )
    return skeleton


def _on_pre_activate_changes(*_args: object) -> None:
    # Builtin hooks propagate, and this one runs inside Activate Changes: an
    # unwritable maps.d or a folder-tree read error would abort the activation for
    # the whole site. Maps is not core-critical (unlike mkeventd's config
    # regeneration) — the folder-tree map just keeps serving the previous skeleton
    # — so log and let the activation finish.
    try:
        path = folder_perms_path()
        path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(path, key=VAR_FOLDER_PERMS, value=_resolve_folder_skeleton())
    except Exception:
        logger.exception(
            "Cannot write the Maps folder permissions to %(path)s",
            {"path": folder_perms_path()},
        )


def register() -> None:
    # Resolve on every activation so the skeleton lands in the replication
    # snapshot shipped to remote sites (mirrors mkeventd's pre-activate hook).
    hooks.register_builtin("pre-activate-changes", _on_pre_activate_changes)
