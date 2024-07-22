#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_prometheus_arguments(
    params: Mapping[str, object], hostname: str, ipaddress: str | None
) -> list[object]:
    params_without_auth = {k: v for k, v in params.items() if k != "auth_basic"}
    args: list[object] = [
        "--config",
        repr({**params_without_auth, "host_address": ipaddress, "host_name": hostname}),
    ]
    match params.get("auth_basic"):
        case ("auth_login", {"username": username, "password": password}):
            args += [
                "auth_login",
                "--username",
                username,
                "--password-reference",
                passwordstore_get_cmdline("%s", password),
            ]
        case ("auth_token", {"token": token}):
            args += [
                "auth_token",
                "--token",
                passwordstore_get_cmdline("%s", token),
            ]
    return args


special_agent_info["prometheus"] = agent_prometheus_arguments
