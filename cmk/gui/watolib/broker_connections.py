#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from pathlib import Path

from livestatus import BrokerConnection, BrokerConnections, BrokerSite, ConnectionId

from cmk.ccc import store

from cmk.utils import paths

from cmk.gui.config import active_config
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile


class BrokerConnectionsConfigFile(WatoSingleConfigFile[BrokerConnections]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=Path(paths.default_config_dir + "/multisite.d/broker_connections.mk"),
            config_variable="broker_connections",
            spec_class=BrokerConnections,
        )

    def _load_file(self, lock: bool) -> BrokerConnections:
        if not self._config_file_path.exists():
            return BrokerConnections({})

        if (
            connections_from_file := store.load_from_mk_file(
                self._config_file_path,
                key=self._config_variable,
                default={},
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

    def save(self, cfg: BrokerConnections) -> None:
        connections_dict = {k: asdict(v) for k, v in cfg.items()}
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            str(self._config_file_path),
            self._config_variable,
            connections_dict,
            pprint_value=active_config.wato_pprint_config,
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(BrokerConnectionsConfigFile())
