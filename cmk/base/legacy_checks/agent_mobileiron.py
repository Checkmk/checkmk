#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, Mapping, Optional, Sequence, Tuple, Union

from cmk.base.check_api import get_http_proxy, passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_mobileiron_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: Optional[str]
) -> Sequence[Union[str, Tuple[str, str, str]]]:
    args = [
        elem
        for chunk in (
            ("-u", params["username"]) if "username" in params else (),
            ("-p", passwordstore_get_cmdline("%s", params["password"]))
            if "password" in params
            else (),
            ("--partition", ",".join(params["partition"])) if "partition" in params else (),
            ("--hostname", hostname),
        )
        for elem in chunk
    ]
    if proxy_setting := params.get("proxy"):
        args += [
            "--proxy",
            get_http_proxy(proxy_setting).serialize(),
        ]

    for regex_platform_type in ("android-regex", "ios-regex", "other-regex"):
        if regex_platform_type in params:
            for expression in params[regex_platform_type]:
                args.append(f"--{regex_platform_type}={expression}")

    for key_field in params["key-fields"]:
        args.append("--key-fields")
        args.append(key_field)

    return args


special_agent_info["mobileiron"] = agent_mobileiron_arguments  # pylint: disable=undefined-variable
