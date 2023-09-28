#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.config import special_agent_info


def agent_allnet_ip_sensoric_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    return [
        *(["--timeout", "%d" % params["timeout"]] if "timeout" in params else []),
        ipaddress or hostname,
    ]


special_agent_info["allnet_ip_sensoric"] = agent_allnet_ip_sensoric_arguments
