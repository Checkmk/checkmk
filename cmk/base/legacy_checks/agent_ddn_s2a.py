#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_ddn_s2a_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    return [
        ipaddress or hostname,
        "%d" % params.get("port", 8008),
        params["username"],
        passwordstore_get_cmdline("%s", params["password"]),
    ]


special_agent_info["ddn_s2a"] = agent_ddn_s2a_arguments
