#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.plugins.aws.server_side_calls.aws_status_agent_call import special_agent_aws_status
from cmk.server_side_calls.v1 import HostConfig
from cmk.server_side_calls_backend.config_processing import process_configuration_to_parameters


def test_aws_status_fs_values_to_args() -> None:
    # GIVEN
    value = {"regions_to_monitor": ["ap_northeast_2", "ca_central_1"]}
    params = process_configuration_to_parameters(value)

    # WHEN
    special_agent_calls = list(special_agent_aws_status(params.value, HostConfig(name="foo")))

    # THEN
    assert len(special_agent_calls) == 1
    special_agent_call = special_agent_calls[0]
    assert special_agent_call.command_arguments == [
        "ap-northeast-2",
        "ca-central-1",
    ]
