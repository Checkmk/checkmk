#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import (
    ConfigTaskAlreadyExists,
    ConfigTaskCreated,
    ConfigTaskCreationFailed,
    ConfigTaskFactory,
)
from cmk.relay_protocols.tasks import UpdateConfigResponse

# TODO Question: should we use ConfigTaskFactory directly instead of ActivateConfigHandler?


@dataclasses.dataclass(frozen=True)
class ActivateConfigHandler:
    config_task_factory: ConfigTaskFactory

    def process(self) -> UpdateConfigResponse:
        config_creation_results = self.config_task_factory.create_for_all_relays()
        return UpdateConfigResponse(
            created=[
                r.relay_id for r in config_creation_results if isinstance(r, ConfigTaskCreated)
            ],
            pending=[
                r.relay_id
                for r in config_creation_results
                if isinstance(r, ConfigTaskAlreadyExists)
            ],
            failed={
                r.relay_id: str(r.exception)
                for r in config_creation_results
                if isinstance(r, ConfigTaskCreationFailed)
            },
        )
