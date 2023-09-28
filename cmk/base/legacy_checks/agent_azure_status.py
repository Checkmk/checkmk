#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.config import special_agent_info


def agent_azure_status_arguments(
    params: Mapping[str, Any], _hostname: str, _ipaddress: str | None
) -> Sequence[str]:
    return params["regions"]


special_agent_info["azure_status"] = agent_azure_status_arguments
