#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.agent_registration import get_uuid_link_manager

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class AgentRegistration(UpdateAction):
    """Change absolute paths in registered hosts symlinks in var/agent-receiver/received-outputs to relative"""

    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        link_manager = get_uuid_link_manager()
        for link in link_manager:
            if link.target.is_absolute():
                link.unlink()
                link_manager.create_link(link.hostname, link.uuid, push_configured=False)


update_action_registry.register(
    AgentRegistration(
        name="fix_agent_registration_symlinks",
        title="Change absolute paths in registered hosts symlinks to relative",
        sort_index=100,  # can run whenever
    )
)
