#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_smb_share_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    default_ipaddress = ipaddress if ipaddress else ""
    args = [params.get("hostname", hostname), params.get("ip_address", default_ipaddress)]

    if authentication := params.get("authentication"):
        args.append("--username")
        args.append(authentication[0])
        args.append("--password")
        args.append(passwordstore_get_cmdline("%s", authentication[1]))

    if patterns := params.get("patterns"):
        args.append("--patterns")
        args.extend(patterns)

    if params.get("recursive", False):
        args.append("--recursive")

    return args


special_agent_info["smb_share"] = agent_smb_share_arguments
