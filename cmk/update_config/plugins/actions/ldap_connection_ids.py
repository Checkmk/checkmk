#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from copy import copy
from logging import Logger

from cmk.gui.plugins.userdb.utils import load_connection_config, save_connection_config

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateLdapConnectionIds(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        result = []
        for config in load_connection_config():
            if config["type"] == "ldap" and re.search(r"\s", config["id"]):
                new_config = copy(config)
                new_config["id"] = re.sub(r"\s", "_", new_config["id"])

                logger.debug("Updating LDAP config id %s to %s", config["id"], new_config["id"])
                result.append(new_config)
            else:
                result.append(config)
        if len(result) > 0:
            save_connection_config(result)
            logger.debug("Updated %i LDAP connections", len(result))


update_action_registry.register(
    UpdateLdapConnectionIds(
        name="ldap_connection_ids", title="Update LDAP connection ids", sort_index=10
    )
)
