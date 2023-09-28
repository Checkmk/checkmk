#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import typing
from collections.abc import Sequence

from cmk.base.config import special_agent_info


class Params(typing.TypedDict):
    regions: Sequence[str]


def agent_aws_status_arguments(
    params: Params, _hostname: str, _ipaddress: None | str
) -> Sequence[str]:
    return params["regions"]


special_agent_info["aws_status"] = agent_aws_status_arguments
