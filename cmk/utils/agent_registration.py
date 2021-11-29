#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, Iterator, Mapping, NamedTuple, Optional
from uuid import UUID

from cmk.utils.type_defs import HostName


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

    def create_link(self, hostname: HostName, uuid: UUID) -> None:
        """Create a link for encryption or push agent

        Make '<self._received_outputs_dir>/<uuid>' the only (!) symlink pointing to the folder
        '<self._data_source_dir>/<hostname>'.
        """
        if self._find_and_cleanup_existing_links(hostname, uuid):
            return

        source = self._received_outputs_dir / f"{uuid}"
        self._received_outputs_dir.mkdir(parents=True, exist_ok=True)

        target_dir = self._data_source_dir / f"{hostname}"
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
            host_config = host_configs.get(link.hostname)
            if host_config is None:
                link.unlink()

            elif host_config.get("cmk_agent_connection", "") != "push-agent":
                # Symlink must be kept for the pull case: we need the uuid<->hostname mapping.
                link.unlink_target()
