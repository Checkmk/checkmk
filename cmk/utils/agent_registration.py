#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, List, Mapping, NamedTuple, Optional, Sequence, Tuple
from uuid import UUID

import cmk.utils.paths
from cmk.utils.type_defs import HostName


def get_r4r_filepath(folder: Path, uuid: UUID) -> Path:
    return folder.joinpath(f"{uuid}.json")


def get_uuid_link_manager() -> UUIDLinkManager:
    return UUIDLinkManager(
        received_outputs_dir=cmk.utils.paths.received_outputs_dir,
        data_source_dir=cmk.utils.paths.data_source_push_agent_dir,
    )


class UUIDLink(NamedTuple):
    source: Path
    target: Path

    @property
    def uuid(self) -> UUID:
        return UUID(self.source.name)

    @property
    def hostname(self) -> HostName:
        return HostName(self.target.name)

    def unlink(self) -> None:
        self.unlink_source()
        self.unlink_target()

    def unlink_source(self) -> None:
        self.source.unlink(missing_ok=True)

    def unlink_target(self) -> None:
        try:
            for filepath in self.target.iterdir():
                filepath.unlink(missing_ok=True)
            self.target.rmdir()
        except FileNotFoundError:  # from iterdir
            pass


class UUIDLinkManager:
    def __init__(self, *, received_outputs_dir: Path, data_source_dir: Path) -> None:
        self._received_outputs_dir = received_outputs_dir
        self._data_source_dir = data_source_dir

    def __iter__(self) -> Iterator[UUIDLink]:
        if not self._received_outputs_dir.exists():
            return

        for source in self._received_outputs_dir.iterdir():
            yield UUIDLink(source=source, target=source.readlink())

    def get_uuid(self, host_name: HostName) -> Optional[UUID]:
        for link in self:
            if link.hostname == host_name:
                return link.uuid
        return None

    def create_link(self, hostname: HostName, uuid: UUID, *, create_target_dir: bool) -> None:
        """Create a link for encryption or push agent

        Make '<self._received_outputs_dir>/<uuid>' the only (!) symlink pointing to the folder
        '<self._data_source_dir>/<hostname>'.

        For push agents we need to create the target dir; otherwise not.
        """
        if self._find_and_cleanup_existing_links(hostname, uuid):
            return

        self._received_outputs_dir.mkdir(parents=True, exist_ok=True)
        source = self._received_outputs_dir / f"{uuid}"

        target_dir = self._data_source_dir / f"{hostname}"
        if create_target_dir:
            target_dir.mkdir(parents=True, exist_ok=True)

        source.symlink_to(target_dir)

    def _find_and_cleanup_existing_links(self, hostname: HostName, uuid: UUID) -> bool:
        for link in self:
            if link.hostname != hostname:
                continue
            if link.uuid == uuid:
                return True
            link.unlink_source()
        return False

    def update_links(self, host_configs: Mapping[HostName, Mapping[str, Any]]) -> None:
        for link in self:
            if (host_config := host_configs.get(link.hostname)) is None:
                if self._is_ready_or_discoverable(link.uuid):
                    # Host may not be synced yet, thus we check if UUID is in READY or DISCOVERABLE
                    # folder.
                    continue
                link.unlink()
            else:
                if host_config.get("cmk_agent_connection", "") == "push-agent":
                    target_dir = self._data_source_dir / link.hostname
                    target_dir.mkdir(parents=True, exist_ok=True)
                else:
                    # Symlink must be kept for the pull case: we need the uuid<->hostname mapping.
                    link.unlink_target()

    @staticmethod
    def _is_ready_or_discoverable(uuid: UUID) -> bool:
        return any(
            get_r4r_filepath(folder, uuid).exists()
            for folder in [cmk.utils.paths.r4r_ready_dir, cmk.utils.paths.r4r_discoverable_dir]
        )

    def rename(
        self, successful_renamings: Sequence[Tuple[HostName, HostName]]
    ) -> Sequence[Tuple[HostName, HostName]]:
        from_old_to_new = dict(successful_renamings)
        renamed: List[Tuple[HostName, HostName]] = []
        for link in self:
            old_name = link.hostname
            if (new_name := from_old_to_new.get(old_name)) is not None:
                create_target_dir = (self._data_source_dir / old_name).exists()

                link.unlink_source()
                self.create_link(new_name, link.uuid, create_target_dir=create_target_dir)

                renamed.append((old_name, new_name))

        return sorted(renamed)
