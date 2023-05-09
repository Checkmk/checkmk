#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# 2019-01-17, comNET GmbH, Fabian Binder


# mypy: disable-error-code="list-item"

from typing import Any, Mapping, Optional, Sequence

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_zerto_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: Optional[str]
) -> Sequence[str]:
    return [
        "--authentication",
        params.get("authentication", "windows"),
        "-u",
        params["username"],
        "-p",
        passwordstore_get_cmdline("%s", params["password"]),
        ipaddress or hostname,
    ]


special_agent_info["zerto"] = agent_zerto_arguments
