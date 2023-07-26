#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, Mapping, Optional, Sequence

from cmk.base.config import special_agent_info


def agent_ibmsvc_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: Optional[str]
) -> Sequence[str]:
    args = ["-u", params["user"], "-i", ",".join(params["infos"])]
    if params["accept-any-hostkey"] is True:
        args += ["--accept-any-hostkey"]

    args.append(ipaddress or hostname)
    return args


special_agent_info["ibmsvc"] = agent_ibmsvc_arguments
