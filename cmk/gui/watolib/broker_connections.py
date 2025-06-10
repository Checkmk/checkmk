#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import override, TypedDict

from livestatus import BrokerConnection, BrokerConnections, BrokerSite, ConnectionId

from cmk.ccc import store
from cmk.ccc.site import SiteId

from cmk.utils import paths

from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile


class BrokerConnectionsConfigFile(WatoSingleConfigFile[BrokerConnections]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=paths.default_config_dir / "multisite.d/broker_connections.mk",
            config_variable="broker_connections",
            spec_class=BrokerConnections,
        )

    @override
    def _load_file(self, *, lock: bool) -> BrokerConnections:
        if not self._config_file_path.exists():
            return BrokerConnections({})

        if (
            connections_from_file := store.load_from_mk_file(
                self._config_file_path,
                key=self._config_variable,
                default=dict[str, dict[str, dict[str, SiteId]]](),
                lock=lock,
            )
        ) is None:
            return BrokerConnections({})

        return BrokerConnections(
            {
                ConnectionId(k): BrokerConnection(
                    connecter=BrokerSite(v["connecter"]["site_id"]),
                    connectee=BrokerSite(v["connectee"]["site_id"]),
                )
                for k, v in connections_from_file.items()
            }
        )

    @override
    def save(self, cfg: BrokerConnections, pprint_value: bool) -> None:
        connections_dict = {k: asdict(v) for k, v in cfg.items()}
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            self._config_file_path,
            key=self._config_variable,
            value=connections_dict,
            pprint_value=pprint_value,
        )


class SiteConnectionInfo(TypedDict, total=True):
    site_id: str


class BrokerConnectionInfo(TypedDict, total=True):
    connecter: SiteConnectionInfo
    connectee: SiteConnectionInfo


@dataclass
class SiteConnectionData:
    site_id: SiteId


@dataclass
class BrokerConnectionConfig:
    connection_id: ConnectionId
    connecter: SiteConnectionData
    connectee: SiteConnectionData

    @classmethod
    def from_internal(
        cls, connection_id: ConnectionId, internal_config: BrokerConnection
    ) -> BrokerConnectionConfig:
        return cls(
            connection_id=connection_id,
            connecter=SiteConnectionData(site_id=internal_config.connecter.site_id),
            connectee=SiteConnectionData(site_id=internal_config.connectee.site_id),
        )

    @classmethod
    def from_external(
        cls, connection_id: str, external_config: BrokerConnectionInfo
    ) -> BrokerConnectionConfig:
        return cls(
            connection_id=ConnectionId(connection_id),
            connecter=SiteConnectionData(site_id=SiteId(external_config["connecter"]["site_id"])),
            connectee=SiteConnectionData(site_id=SiteId(external_config["connectee"]["site_id"])),
        )

    def to_external(self) -> BrokerConnectionInfo:
        return BrokerConnectionInfo(
            connecter=SiteConnectionInfo(site_id=self.connecter.site_id),
            connectee=SiteConnectionInfo(site_id=self.connectee.site_id),
        )

    def to_internal(self) -> BrokerConnection:
        return BrokerConnection(
            connecter=BrokerSite(site_id=self.connecter.site_id),
            connectee=BrokerSite(site_id=self.connectee.site_id),
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(BrokerConnectionsConfigFile())
