#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.sites import site_management_registry

from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateMessageBrokerPort(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        site_mgmt = site_management_registry["site_management"]
        configured_sites = site_mgmt.load_sites()
        for site_spec in configured_sites.values():
            site_spec.setdefault("message_broker_port", 5672)
        site_mgmt.save_sites(
            configured_sites,
            activate=False,
            pprint_value=active_config.wato_pprint_config,
        )


update_action_registry.register(
    UpdateMessageBrokerPort(
        name="message_broker_port",
        title="Message broker port of site connections",
        sort_index=30,
    )
)
