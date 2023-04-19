#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, Mapping, Optional, Sequence

from cmk.base.config import special_agent_info


def agent_tinkerforge_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: Optional[str]
) -> Sequence[str]:
    args = ["--host", ipaddress or hostname]

    for par in ["port", "segment_display_uid", "segment_display_brightness"]:
        if par in params:
            args.append("--%s" % par)
            args.append("%s" % params[par])

    return args


special_agent_info["tinkerforge"] = agent_tinkerforge_arguments
