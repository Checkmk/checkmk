#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
from collections.abc import Collection, Generator, Iterable, Mapping
from os.path import relpath
from pathlib import Path
from typing import Final
from uuid import UUID

from cmk.ccc.hostaddress import HostName


class HostAgentConnectionMode(enum.Enum):
    PULL = "pull-agent"
    PUSH = "push-agent"


def get_r4r_filepath(folder: Path, uuid: UUID) -> Path:
    return folder.joinpath(f"{uuid}.json")


def connection_mode_from_host_config(host_config: Mapping[str, object]) -> HostAgentConnectionMode:
    return HostAgentConnectionMode(
        host_config.get(
            "cmk_agent_connection",
            HostAgentConnectionMode.PULL.value,
        )
    )


class UUIDStore:
    """Maintain a lookup for host names to UUIDs.

    This is needed because the fetchers are supposed to notice changes in the
    the hosts UUID right away, not only after activation.
    """

    def __init__(self, uuid_lookup_dir: Path) -> None:
        self.uuid_lookup_dir = uuid_lookup_dir

    def get(self, host_name: HostName) -> UUID | None:
        try:
            return UUID(str((self.uuid_lookup_dir / str(host_name)).readlink()))
        except FileNotFoundError:
            return None

    def set(self, host_name: HostName, uuid: UUID) -> None:
        self.uuid_lookup_dir.mkdir(parents=True, exist_ok=True)
        self.delete(host_name)
        (self.uuid_lookup_dir / str(host_name)).symlink_to(str(uuid))

    def delete(self, host_name: HostName) -> None:
        (self.uuid_lookup_dir / str(host_name)).unlink(missing_ok=True)


class UUIDLinkManager:
    def __init__(
        self,
        *,
        received_outputs_dir: Path,
        data_source_dir: Path,
        r4r_discoverable_dir: Path,
        uuid_lookup_dir: Path,
    ) -> None:
        self.received_outputs_dir: Final = received_outputs_dir
        self.data_source_dir: Final = data_source_dir
        self.r4r_discoverable_dir: Final = r4r_discoverable_dir
        self.uuid_store = UUIDStore(uuid_lookup_dir)

    def __iter__(self) -> Generator[_UUIDLink]:
        if not self.received_outputs_dir.exists():
            return

        for source in self.received_outputs_dir.iterdir():
            try:
                yield _UUIDLink(source=source, target=source.readlink())
            except FileNotFoundError:
                continue

    def unlink(self, host_names: Collection[HostName]) -> None:
        for link in self:
            if link.hostname in host_names:
                link.unlink()
                self.uuid_store.delete(link.hostname)

    def create_link(self, hostname: HostName, uuid: UUID, *, push_configured: bool) -> None:
        """Create a link for encryption or push agent

        Make '<self._received_outputs_dir>/<uuid>' the only (!) symlink pointing to the folder
        '<self._data_source_dir>/<hostname>'.

        For push agents we need to create the target dir; otherwise not.
        """

        if existing_link := self._find_and_cleanup_existing_links(hostname, uuid):
            self._update_link_target_if_necessary(existing_link, push_configured)
            return

        self._create_link(uuid, hostname, self._target_dir(hostname, push_configured))

    def update_links(self, host_configs: Mapping[HostName, Mapping[str, object]]) -> None:
        for link in self:
            if (host_config := host_configs.get(link.hostname)) is None:
                if self._is_discoverable(link.uuid):
                    # Host may not be synced yet, thus we check if UUID is in DISCOVERABLE folder.
                    continue
                link.unlink()
                self.uuid_store.delete(link.hostname)
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
                new_name, link.uuid, push_configured=link.target.parent == self.data_source_dir
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
        self._create_link(existing_link.uuid, existing_link.hostname, target_dir)

    def _target_dir(self, hostname: HostName, is_push_host: bool) -> Path:
        return self.data_source_dir / (f"{hostname}" if is_push_host else f"inactive/{hostname}")

    def _create_link(self, uuid: UUID, host_name: HostName, target_dir: Path) -> None:
        self.uuid_store.set(host_name, uuid)
        self.received_outputs_dir.mkdir(parents=True, exist_ok=True)
        source = self.received_outputs_dir / f"{uuid}"
        source.unlink(missing_ok=True)
        source.symlink_to(relpath(target_dir, self.received_outputs_dir))

    def _is_discoverable(self, uuid: UUID) -> bool:
        return get_r4r_filepath(self.r4r_discoverable_dir, uuid).exists()


class _UUIDLink:
    def __init__(self, *, source: Path, target: Path) -> None:
        self.source: Final = source
        self.target: Final = target
        self.uuid: Final = UUID(self.source.name)
        self.hostname: Final = HostName(self.target.name)

    def unlink(self) -> None:
        self.source.unlink(missing_ok=True)
