#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Container, Iterator, Mapping, Sequence
from os.path import relpath
from pathlib import Path
from typing import Any, NamedTuple
from uuid import UUID

import cmk.utils.paths
from cmk.utils.type_defs import HostAgentConnectionMode, HostName


def get_r4r_filepath(folder: Path, uuid: UUID) -> Path:
    return folder.joinpath(f"{uuid}.json")


def get_uuid_link_manager() -> UUIDLinkManager:
    return UUIDLinkManager(
        received_outputs_dir=cmk.utils.paths.received_outputs_dir,
        data_source_dir=cmk.utils.paths.data_source_push_agent_dir,
    )


def connection_mode_from_host_config(host_config: Mapping[str, object]) -> HostAgentConnectionMode:
    return HostAgentConnectionMode(
        host_config.get(
            "cmk_agent_connection",
            HostAgentConnectionMode.PULL.value,
        )
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
        self.source.unlink(missing_ok=True)


class UUIDLinkManager:
    def __init__(self, *, received_outputs_dir: Path, data_source_dir: Path) -> None:
        self._received_outputs_dir = received_outputs_dir
        self._data_source_dir = data_source_dir

    def __iter__(self) -> Iterator[UUIDLink]:
        if not self._received_outputs_dir.exists():
            return

        for source in self._received_outputs_dir.iterdir():
            yield UUIDLink(source=source, target=source.readlink())

    def unlink(self, host_names: Container[HostName]) -> None:
        for link in self:
            if link.hostname in host_names:
                link.unlink()

    def get_uuid(self, host_name: HostName) -> UUID | None:
        for link in self:
            if link.hostname == host_name:
                return link.uuid
        return None

    def create_link(self, hostname: HostName, uuid: UUID, *, push_configured: bool) -> None:
        """Create a link for encryption or push agent

        Make '<self._received_outputs_dir>/<uuid>' the only (!) symlink pointing to the folder
        '<self._data_source_dir>/<hostname>'.

        For push agents we need to create the target dir; otherwise not.
        """
        existing_link = self._find_and_cleanup_existing_links(hostname, uuid)
        target_dir = self._data_source_dir / (
            f"{hostname}" if push_configured else f"inactive/{hostname}"
        )

        if existing_link is not None and existing_link.target == target_dir:
            return

        self._received_outputs_dir.mkdir(parents=True, exist_ok=True)
        source = self._received_outputs_dir / f"{uuid}"

        source.unlink(missing_ok=True)
        source.symlink_to(relpath(target_dir, self._received_outputs_dir))

    def _find_and_cleanup_existing_links(self, hostname: HostName, uuid: UUID) -> UUIDLink | None:
        found: UUIDLink | None = None
        for link in self:
            if link.hostname != hostname:
                continue
            if link.uuid != uuid:
                link.unlink()
                continue
            found = link
        return found

    def update_links(self, host_configs: Mapping[HostName, Mapping[str, Any]]) -> None:
        for link in self:
            if (host_config := host_configs.get(link.hostname)) is None:
                if self._is_discoverable(link.uuid):
                    # Host may not be synced yet, thus we check if UUID is in DISCOVERABLE folder.
                    continue
                link.unlink()
            else:
                self.create_link(
                    link.hostname,
                    link.uuid,
                    push_configured=connection_mode_from_host_config(host_config)
                    is HostAgentConnectionMode.PUSH,
                )

    @staticmethod
    def _is_discoverable(uuid: UUID) -> bool:
        return get_r4r_filepath(cmk.utils.paths.r4r_discoverable_dir, uuid).exists()

    def rename(
        self, successful_renamings: Sequence[tuple[HostName, HostName]]
    ) -> Sequence[tuple[HostName, HostName]]:
        from_old_to_new = dict(successful_renamings)
        renamed: list[tuple[HostName, HostName]] = []
        for link in self:
            old_name = link.hostname
            if (new_name := from_old_to_new.get(old_name)) is None:
                continue

            link.unlink()
            self.create_link(
                new_name, link.uuid, push_configured=link.target.parent == self._data_source_dir
            )
            renamed.append((old_name, new_name))

        return sorted(renamed)
