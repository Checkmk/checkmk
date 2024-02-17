#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import subprocess
from logging import Logger

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class ComputeAPISpec(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        subprocess.check_call(["cmk-compute-api-spec"])


update_action_registry.register(
    ComputeAPISpec(
        name="compute_api_spec",
        title="Compute REST API specification",
        sort_index=999,  # Run after all other actions
    )
)
