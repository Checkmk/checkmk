#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Preparing the site configuration in distributed setups for synchronization"""

import abc
import enum
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, override, Self

from livestatus import SiteConfiguration, SiteGlobals

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId

import cmk.utils.paths

from cmk.gui.log import logger
from cmk.gui.userdb import user_sync_default_config
from cmk.gui.watolib.config_domain_name import wato_fileheader

from cmk.messaging import rabbitmq

Command = list[str]


class ReplicationPathType(enum.Enum):
    FILE = "file"
    DIR = "dir"


@dataclass(frozen=True, kw_only=True)
class ReplicationPath:
    _PATTERNS_INTERMEDIATE_STORE_FILES = frozenset([re.compile(r"^\..*\.new.*")])

    ty: ReplicationPathType
    ident: str
    site_path: str
    excludes_exact_match: frozenset[str]
    excludes_regex_match: frozenset[re.Pattern[str]]

    @classmethod
    def make(
        cls,
        *,
        ty: ReplicationPathType,
        ident: str,
        site_path: str,
        excludes_exact_match: Iterable[str] = (),
        excludes_regex_match: Iterable[str] = (),
    ) -> Self:
        if site_path.startswith("/"):
            raise Exception("ReplicationPath.site_path must be a path relative to the site root")
        cleaned_path = site_path.rstrip("/")

        return cls(
            ty=ty,
            ident=ident,
            site_path=cleaned_path,
            excludes_exact_match=frozenset(excludes_exact_match),
            excludes_regex_match=frozenset(re.compile(pattern) for pattern in excludes_regex_match)
            | cls._PATTERNS_INTERMEDIATE_STORE_FILES,
        )

    def is_excluded(self, entry: str) -> bool:
        return entry in self.excludes_exact_match or any(
            pattern.match(entry) for pattern in self.excludes_regex_match
        )

    def serialize(self) -> tuple[str, str, str, list[str], list[str]]:
        return (
            self.ty.value,
            self.ident,
            self.site_path,
            list(self.excludes_exact_match),
            [pattern.pattern for pattern in self.excludes_regex_match],
        )

    @classmethod
    def deserialize(cls, serialized: object) -> Self:
        if not isinstance(serialized, tuple):
            raise TypeError(serialized)
        match serialized:
            # Legacy format, drop in 2.6.
            # We need this in 2.5 to stay compatible with 2.4 central sites. A 2.5 remote site must
            # support both formats.
            case (
                str(raw_ty),
                str(ident),
                str(site_path),
                excludes_exact_match,
            ):
                return cls.make(
                    ty=ReplicationPathType(raw_ty),
                    ident=ident,
                    site_path=site_path,
                    excludes_exact_match=excludes_exact_match,
                )
            case (
                str(raw_ty),
                str(ident),
                str(site_path),
                excludes_exact_match,
                excludes_regex_match,
            ):
                return cls.make(
                    ty=ReplicationPathType(raw_ty),
                    ident=ident,
                    site_path=site_path,
                    excludes_exact_match=excludes_exact_match,
                    excludes_regex_match=excludes_regex_match,
                )
            case _:
                raise TypeError(serialized)


class ReplicationPathRegistry(Registry[ReplicationPath]):
    @override
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
                "user_sync", user_sync_default_config(site_config, site_id)
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
