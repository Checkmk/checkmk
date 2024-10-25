#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.config import special_agent_info

from cmk.agent_based.v0_unstable_legacy import passwordstore_get_cmdline


def agent_ruckus_spot_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    args = []
    if params["address"] is True:
        args += ["--address", ipaddress or hostname, "%s" % params["port"]]
    else:
        args += ["--address", params["address"], "%s" % params["port"]]
    args += ["--venueid", params["venueid"]]
    args += ["--apikey", passwordstore_get_cmdline("%s", params["api_key"])]
    if "cmk_agent" in params:
        args += ["--agent_port", "%s" % params["cmk_agent"]["port"]]
    return args


special_agent_info["ruckus_spot"] = agent_ruckus_spot_arguments
