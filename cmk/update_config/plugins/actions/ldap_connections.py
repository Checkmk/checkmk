#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.userdb import LDAPUserConnectionConfig, UserConnectionConfigFile

from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateLDAPConnections(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        # These changes were actually made a long time ago. The migrations were just only be done
        # during runtime and never persisted, so the we can not be sure that the migration was done for
        # all connections. So we need to keep the migration for the 2.4 here and can drop it afterwards.
        config_file = UserConnectionConfigFile()
        connections = config_file.load_for_modification()
        migrated = False
        for connection in connections:
            if connection["type"] == "ldap":
                migrated |= self._migrate_config(connection)

        if migrated:
            config_file.save(connections, pprint_value=active_config.wato_pprint_config)

    def _migrate_config(self, cfg: LDAPUserConnectionConfig) -> bool:
        migrated = False
        # For a short time in git master the directory_type could be:
        # ('ad', {'discover_nearest_dc': True/False})
        if (
            isinstance(cfg["directory_type"], tuple)
            and cfg["directory_type"][0] == "ad"
            and "discover_nearest_dc" in cfg["directory_type"][1]
        ):
            auto_discover = cfg["directory_type"][1]["discover_nearest_dc"]  # type: ignore[typeddict-item]

            if not auto_discover:
                cfg["directory_type"] = "ad"  # type: ignore[typeddict-item]
            else:
                cfg["directory_type"] = (  # type: ignore[typeddict-item]
                    cfg["directory_type"][0],
                    {
                        "connect_to": (
                            "discover",
                            {
                                "domain": cfg["server"],  # type: ignore[typeddict-item]
                            },
                        ),
                    },
                )
            migrated = True

        if not isinstance(cfg["directory_type"], tuple) and "server" in cfg:
            # Old separate configuration of directory_type and server
            servers = {
                "server": cfg["server"],
            }

            if "failover_servers" in cfg:
                servers["failover_servers"] = cfg["failover_servers"]

            cfg["directory_type"] = (
                cfg["directory_type"],
                {
                    "connect_to": ("fixed_list", servers),
                },
            )
            migrated = True

        return migrated


update_action_registry.register(
    UpdateLDAPConnections(
        name="update_ldap_connections",
        title="Update LDAP connections",
        sort_index=100,  # can run whenever
    )
)
