#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, Mapping, NamedTuple, Optional, Sequence

from cmk.base.config import special_agent_info

# NOTE: This code is temporarily duplicated from cmk/base/config.py to resolve
# a layering violation.
# This will be resovled with CMK-3812.
# DO NOT USE THIS!!!


class SpecialAgentConfiguration(NamedTuple):
    args: Sequence[str]
    # None makes the stdin of subprocess /dev/null
    stdin: Optional[str]


def agent_alertmanager_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: Optional[str]
) -> SpecialAgentConfiguration:
    alertmanager_params = {**params, "host_address": ipaddress, "host_name": hostname}
    return SpecialAgentConfiguration([], repr(alertmanager_params))


special_agent_info["alertmanager"] = agent_alertmanager_arguments
