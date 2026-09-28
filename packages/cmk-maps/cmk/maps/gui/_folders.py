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
user-independent, so one file serves every viewer. The central site writes it as
a snapshot artifact, before the activation takes its snapshots, so the file lands
in the same activation's replication snapshot. The remote sites don't resolve it
themselves: their folders are the central site's.
"""

from pathlib import Path

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.log import logger
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.snapshot_artifacts import SnapshotArtifact, SnapshotArtifactRegistry
from cmk.maps.shared.config_vars import FolderPermEntry, VAR_FOLDER_PERMS


def folder_perms_path() -> Path:
    return cmk.utils.paths.default_config_dir / "maps.d" / "wato" / "folder_perms.mk"


def _resolve_folder_skeleton(tree: FolderTree) -> list[FolderPermEntry]:
    """Every SETUP folder with its title, stable id and effective read-permitted
    contact groups, resolved via the real ``Folder.groups()``.

    ``groups()`` returns ``(permitted_groups, host_contact_groups, ...)``; the
    daemon only needs the first — the effective *read* permission incl. the
    ``recurse_perms`` ancestor inheritance.
    """
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


def _is_written(path: Path, skeleton: list[FolderPermEntry]) -> bool:
    # A file that cannot be read counts as changed, so the next write repairs it.
    try:
        written: list[FolderPermEntry] = store.load_from_mk_file(
            path, key=VAR_FOLDER_PERMS, default=[], lock=False
        )
    except MKGeneralException:
        return False
    return written == skeleton


def write_folder_skeleton(tree: FolderTree) -> None:
    # This runs inside Activate Changes, where an exception aborts the activation:
    # an unwritable maps.d or a folder-tree read error would do that for the whole
    # site. Maps is not core-critical — the folder-tree map just keeps serving the
    # previous skeleton — so log and let the activation finish.
    try:
        path = folder_perms_path()
        skeleton = _resolve_folder_skeleton(tree)
        # Written on every activation, so leave an unchanged file untouched.
        if _is_written(path, skeleton):
            return
        path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(path, key=VAR_FOLDER_PERMS, value=skeleton)
    except Exception:
        logger.exception(
            "Cannot write the Maps folder permissions to %(path)s",
            {"path": folder_perms_path()},
        )


def register(snapshot_artifact_registry: SnapshotArtifactRegistry) -> None:
    snapshot_artifact_registry.register(
        SnapshotArtifact(ident="maps_folder_permissions", write=write_folder_skeleton)
    )
