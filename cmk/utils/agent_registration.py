#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
from collections.abc import Container, Generator, Iterable, Mapping
from os.path import relpath
from pathlib import Path
from typing import Final
from uuid import UUID

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths


class HostAgentConnectionMode(enum.Enum):
    PULL = "pull-agent"
    PUSH = "push-agent"


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


class UUIDLinkManager:
    def __init__(self, *, received_outputs_dir: Path, data_source_dir: Path) -> None:
        self._received_outputs_dir = received_outputs_dir
        self._data_source_dir = data_source_dir

    def __iter__(self) -> Generator[_UUIDLink]:
        if not self._received_outputs_dir.exists():
            return

        for source in self._received_outputs_dir.iterdir():
            try:
                yield _UUIDLink(source=source, target=source.readlink())
            except FileNotFoundError:
                continue

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
        if existing_link := self._find_and_cleanup_existing_links(hostname, uuid):
            self._update_link_target_if_necessary(existing_link, push_configured)
            return

        self._create_link(uuid, self._target_dir(hostname, push_configured))

    def update_links(self, host_configs: Mapping[HostName, Mapping[str, object]]) -> None:
        for link in self:
            if (host_config := host_configs.get(link.hostname)) is None:
                if self._is_discoverable(link.uuid):
                    # Host may not be synced yet, thus we check if UUID is in DISCOVERABLE folder.
                    continue
                link.unlink()
            else:
                self._update_link_target_if_necessary(
                    link,
                    connection_mode_from_host_config(host_config) is HostAgentConnectionMode.PUSH,
                )

    def rename(
        self, successful_renamings: Iterable[tuple[HostName, HostName]]
    ) -> list[tuple[HostName, HostName]]:
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

    def _find_and_cleanup_existing_links(self, hostname: HostName, uuid: UUID) -> _UUIDLink | None:
        found: _UUIDLink | None = None
        for link in self:
            if link.hostname != hostname:
                continue
            if link.uuid != uuid:
                link.unlink()
                continue
            found = link
        return found

    def _update_link_target_if_necessary(
        self, existing_link: _UUIDLink, is_push_host: bool
    ) -> None:
        target_dir = self._target_dir(existing_link.hostname, is_push_host)
        if existing_link.target == target_dir:
            return
        self._create_link(existing_link.uuid, target_dir)

    def _target_dir(self, hostname: HostName, is_push_host: bool) -> Path:
        return self._data_source_dir / (f"{hostname}" if is_push_host else f"inactive/{hostname}")

    def _create_link(self, uuid: UUID, target_dir: Path) -> None:
        self._received_outputs_dir.mkdir(parents=True, exist_ok=True)
        source = self._received_outputs_dir / f"{uuid}"
        source.unlink(missing_ok=True)
        source.symlink_to(relpath(target_dir, self._received_outputs_dir))

    @staticmethod
    def _is_discoverable(uuid: UUID) -> bool:
        return get_r4r_filepath(cmk.utils.paths.r4r_discoverable_dir, uuid).exists()


class _UUIDLink:
    def __init__(self, *, source: Path, target: Path) -> None:
        self.source: Final = source
        self.target: Final = target
        self.uuid: Final = UUID(self.source.name)
        self.hostname: Final = HostName(self.target.name)

    def unlink(self) -> None:
        self.source.unlink(missing_ok=True)
