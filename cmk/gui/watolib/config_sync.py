#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Preparing the site configuration in distributed setups for synchronization"""

import abc
import os
from pathlib import Path
from typing import NamedTuple

from livestatus import SiteConfiguration, SiteGlobals, SiteId

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.plugin_registry import Registry

import cmk.utils.paths

from cmk.gui.log import logger
from cmk.gui.userdb import user_sync_default_config
from cmk.gui.watolib.config_domain_name import wato_fileheader

from cmk.messaging import rabbitmq

Command = list[str]


class _BaseReplicationPath(NamedTuple):
    """Needed for the ReplicationPath class to call __new__ method."""

    ty: str
    ident: str
    site_path: str
    excludes: list[str]


class ReplicationPath(_BaseReplicationPath):
    def __new__(cls, ty: str, ident: str, site_path: str, excludes: list[str]) -> "ReplicationPath":
        if site_path.startswith("/"):
            raise Exception("ReplicationPath.path must be a path relative to the site root")
        cleaned_path = site_path.rstrip("/")

        if ".*new*" not in excludes:
            final_excludes = excludes[:]
            final_excludes.append(".*new*")  # exclude all temporary files
        else:
            final_excludes = excludes

        return super().__new__(
            cls,
            ty=ty,
            ident=ident,
            site_path=cleaned_path,
            excludes=final_excludes,
        )


class ReplicationPathRegistry(Registry[ReplicationPath]):
    def plugin_name(self, instance: ReplicationPath) -> str:
        return instance.ident


replication_path_registry = ReplicationPathRegistry()


class SnapshotSettings(NamedTuple):
    # TODO: Refactor to Path
    snapshot_path: str
    # TODO: Refactor to Path
    work_dir: str
    # TODO: Clarify naming (-> replication path or snapshot component?)
    snapshot_components: list[ReplicationPath]
    component_names: set[str]
    site_config: SiteConfiguration
    rabbitmq_definition: rabbitmq.Definitions


class ABCSnapshotDataCollector(abc.ABC):
    """Prepares files to be synchronized to the remote sites"""

    def __init__(self, site_snapshot_settings: dict[SiteId, SnapshotSettings]) -> None:
        super().__init__()
        self._site_snapshot_settings = site_snapshot_settings
        self._logger = logger.getChild(self.__class__.__name__)

    @abc.abstractmethod
    def prepare_snapshot_files(self) -> None:
        """Site independent preparation of files to be used for the sync snapshots
        This will be called once before iterating over all sites.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_generic_components(self) -> list[ReplicationPath]:
        """Return the site independent snapshot components
        These will be collected by the SnapshotManager once when entering the context manager
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_site_components(
        self, snapshot_settings: SnapshotSettings
    ) -> tuple[list[ReplicationPath], list[ReplicationPath]]:
        """Split the snapshot components into generic and site specific components

        The generic components have the advantage that they only need to be created once for all
        sites and can be shared between the sites to optimize processing."""
        raise NotImplementedError()


def is_user_file(filepath: str) -> bool:
    entry = os.path.basename(filepath)
    return entry.startswith("user_") or entry in ["tableoptions.mk", "treestates.mk", "sidebar.mk"]


def get_site_globals(site_id: SiteId, site_config: SiteConfiguration) -> SiteGlobals:
    site_globals = site_config.get("globals", {}).copy()
    site_globals.update(
        {
            "wato_enabled": not site_config.get("disable_wato", True),
            "userdb_automatic_sync": site_config.get(
                "user_sync", user_sync_default_config(site_id)
            ),
            "user_login": site_config.get("user_login", False),
        }
    )
    return site_globals


def create_distributed_wato_files(base_dir: Path, site_id: SiteId, is_remote: bool) -> None:
    _create_distributed_wato_file_for_base(base_dir, site_id, is_remote)
    _create_distributed_wato_file_for_dcd(base_dir, is_remote)
    _create_distributed_wato_file_for_omd(base_dir, is_remote)


def _create_distributed_wato_file_for_base(
    base_dir: Path, site_id: SiteId, is_remote: bool
) -> None:
    output = wato_fileheader()
    output += (
        "# This file has been created by the master site\n"
        "# push the configuration to us. It makes sure that\n"
        "# we only monitor hosts that are assigned to our site.\n\n"
    )
    output += "distributed_wato_site = '%s'\n" % site_id
    output += "is_wato_slave_site = %r\n" % is_remote

    store.save_text_to_file(base_dir.joinpath("etc/check_mk/conf.d/distributed_wato.mk"), output)


def _create_distributed_wato_file_for_dcd(base_dir: Path, is_remote: bool) -> None:
    if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.CRE:
        return

    output = wato_fileheader()
    output += "dcd_is_wato_remote_site = %r\n" % is_remote

    store.save_text_to_file(base_dir.joinpath("etc/check_mk/dcd.d/wato/distributed.mk"), output)


def _create_distributed_wato_file_for_omd(base_dir: Path, is_remote: bool) -> None:
    output = wato_fileheader()
    output += f"is_wato_remote_site = {is_remote}\n"
    store.save_text_to_file(base_dir / "etc/omd/distributed.mk", output)


def create_rabbitmq_new_definitions_file(base_dir: Path, definition: rabbitmq.Definitions) -> None:
    store.save_text_to_file(base_dir / rabbitmq.NEW_DEFINITIONS_FILE_PATH, definition.dumps())
