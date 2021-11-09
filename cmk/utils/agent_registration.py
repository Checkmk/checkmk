#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Any, Iterator, Mapping, NamedTuple
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
        for filepath in self.target.iterdir():
            filepath.unlink(missing_ok=True)
        self.target.rmdir()


class UUIDLinkManager:
    def __init__(self, *, received_outputs_dir: Path, data_source_dir: Path) -> None:
        self._received_outputs_dir = received_outputs_dir
        self._data_source_dir = data_source_dir

    def __iter__(self) -> Iterator[UUIDLink]:
        if not self._received_outputs_dir.exists():
            return

        for source in self._received_outputs_dir.iterdir():
            yield UUIDLink(
                source=source,
                # Since Python 3.9 pathlib provides Path.readlink()
                target=Path(os.readlink(source)),
            )

    def create_link(self, hostname: HostName, uuid: UUID) -> None:
        """Create a link for encryption (CRE) or push agent (CCE).
        The link points
        - from:          'var/agent_receiver/receive_outputs/<uuid>'
        - to the folder: 'tmp/check_mk/data_source_cache/push_agents/<hostname>'
        (by default).
        """
        self._may_cleanup_old_link(hostname, uuid)

        self._received_outputs_dir.mkdir(parents=True, exist_ok=True)
        source = self._received_outputs_dir.joinpath(str(uuid))

        target_dir = self._data_source_dir.joinpath(hostname)
        target_dir.mkdir(parents=True, exist_ok=True)

        source.symlink_to(target_dir)

    def _may_cleanup_old_link(self, hostname: HostName, uuid: UUID) -> None:
        for link in self:
            if link.hostname == hostname and link.uuid != uuid:
                link.unlink_source()

    def update_links(self, host_configs: Mapping[HostName, Mapping[str, Any]]) -> None:
        for link in self:
            host_config = host_configs.get(link.hostname)
            if host_config is None:
                link.unlink()

            elif host_config.get("cmk_agent_connection", "") != "push-agent":
                # Symlink must be kept for the pull case: we need the uuid<->hostname mapping.
                link.unlink_target()
