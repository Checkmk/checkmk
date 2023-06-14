#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import get_http_proxy, passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_cisco_meraki_arguments(
    params: Mapping[str, Any],
    hostname: str,
    ipaddress: str | None,
) -> Sequence[object]:
    args = [
        hostname,
        passwordstore_get_cmdline("%s", params["api_key"]),
    ]

    if (proxy := params.get("proxy")) is not None:
        args.extend(
            [
                "--proxy",
                get_http_proxy(proxy).serialize(),
            ]
        )

    if sections := params.get("sections"):
        args.extend(["--sections"] + sections)

    if orgs := params.get("orgs"):
        args.extend(["--orgs"] + orgs)

    return args


special_agent_info["cisco_meraki"] = agent_cisco_meraki_arguments
