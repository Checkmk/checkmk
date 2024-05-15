#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# {
#     'port': 443,
#     'password': 'comein',
#     'infos': ['license_state'],
#     'user': 'itsme'
# }


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_rabbitmq_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str | tuple[str, str, str]]:
    args = [
        "-P",
        params["protocol"],
        "-m",
        ",".join(params["sections"]),
        "-u",
        params["user"],
        "-s",
        passwordstore_get_cmdline("%s", params["password"]),
    ]

    if "port" in params:
        args += ["-p", params["port"]]

    if "instance" in params:
        hostname = params["instance"]

    args += [
        "--hostname",
        hostname,
    ]

    return args


special_agent_info["rabbitmq"] = agent_rabbitmq_arguments
