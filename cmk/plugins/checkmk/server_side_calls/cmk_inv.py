#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, model_validator

from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig


class CmkInvParams(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def support_legacy_rule_syntax(cls, data: Any) -> Any:
        if data is None:
            return {}
        return data

    fail_status: int = 1
    hw_changes: int = 0
    sw_changes: int = 0
    sw_missing: int = 0
    nw_changes: int = 0


def generate_cmk_inv_commands(
    params: CmkInvParams,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    yield ActiveCheckCommand(
        service_description="Check_MK HW/SW Inventory",
        command_arguments=[
            "--use-indexed-plugins",
            f"--inv-fail-status={params.fail_status}",
            f"--hw-changes={params.hw_changes}",
            f"--sw-changes={params.sw_changes}",
            f"--sw-missing={params.sw_missing}",
            f"--nw-changes={params.nw_changes}",
            host_config.name,
        ],
    )


active_check_cmk_inv = ActiveCheckConfig(
    name="cmk_inv",
    parameter_parser=CmkInvParams.model_validate,
    commands_function=generate_cmk_inv_commands,
)
