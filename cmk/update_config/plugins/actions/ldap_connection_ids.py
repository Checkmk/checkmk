#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import re
from copy import copy
from logging import Logger

from cmk.gui.plugins.userdb.utils import load_connection_config, save_connection_config
from cmk.gui.userdb import load_users, save_users

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateLdapConnectionIds(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        new_connections = []
        replaced_connections = {}
        for config in load_connection_config():
            if config["type"] == "ldap" and re.search(r"\s", config["id"]):
                new_config = copy(config)
                new_config["id"] = re.sub(r"\s", "_", new_config["id"])

                replaced_connections[config["id"]] = new_config["id"]
                new_connections.append(new_config)
                logger.debug("Updating LDAP config id %s to %s", config["id"], new_config["id"])
            else:
                new_connections.append(config)

        updated_users = {}
        for user_id, user_spec in load_users().items():
            if user_spec["connector"] in replaced_connections:
                new_user_spec = copy(user_spec)
                new_user_spec["connector"] = replaced_connections[user_spec["connector"]]

                logger.debug(
                    "Updating LDAP user %s (from connection previously named %s)",
                    user_id,
                    user_spec["connector"],
                )
                updated_users[user_id] = new_user_spec

        if len(new_connections) > 0:
            save_connection_config(new_connections)
            save_users(updated_users, datetime.datetime.now())
            logger.debug(
                "Updated %i LDAP connections and with %i users",
                len(new_connections),
                len(updated_users),
            )


update_action_registry.register(
    UpdateLdapConnectionIds(
        name="ldap_connection_ids", title="Update LDAP connection ids", sort_index=10
    )
)
