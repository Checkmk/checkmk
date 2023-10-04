#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_appdynamics_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    args = [
        "-u",
        params["username"],
        "-p",
        passwordstore_get_cmdline("%s", params["password"]),
    ]

    if "port" in params:
        args += ["-P", "%d" % params["port"]]

    if "timeout" in params:
        args += ["-t", "%d" % params["timeout"]]

    args += [
        ipaddress or hostname,
        params["application"],
    ]
    return args


special_agent_info["appdynamics"] = agent_appdynamics_arguments
