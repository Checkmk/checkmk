#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_jolokia_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    arglist = ["--server", ipaddress or hostname]

    for param in ["port", "suburi", "instance", "protocol"]:
        if param in params:
            arglist += ["--%s" % param, "%s" % params[param]]

    if login := params.get("login"):
        user, password, mode = login
        arglist += [
            "--user",
            user,
            "--password",
            passwordstore_get_cmdline("%s", password),
            "--mode",
            mode,
        ]

    return arglist


special_agent_info["jolokia"] = agent_jolokia_arguments
