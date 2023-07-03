#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_arguments_pure_storage_fa(
    params: Mapping[str, object], hostname: str, ipaddress: str | None
) -> Sequence[str | tuple[str, str, str]]:
    args: list[str | tuple[str, str, str]] = (
        ["--timeout", str(timeout)] if (timeout := params.get("timeout")) else []
    )

    cert_verify = params.get("ssl", True)
    if cert_verify is False:
        args.append("--no-cert-check")
    elif cert_verify is True:
        args += ["--cert-server-name", hostname]
    else:
        args += ["--cert-server-name", str(cert_verify)]

    api_token = params.get("api_token")
    if isinstance(api_token, (str, tuple)):
        args += ["--api-token", passwordstore_get_cmdline("%s", api_token)]

    return [*args, ipaddress or hostname]


special_agent_info["pure_storage_fa"] = agent_arguments_pure_storage_fa
