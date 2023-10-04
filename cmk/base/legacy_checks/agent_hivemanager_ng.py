#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# {
#     'url': 'https://cloud.aerohive.com',
#     'vhm_id': '12345',
#     'api_token': 'SDLKFJ32401ac1KSjKLLWIUDSKDJW',
#     'client_id': '123a4b56',
#     'client_secret': '1abc23456d13098123098e',
#     'redirect_url': 'https://www.getpostman.com/oauth2/callback'
# }


# mypy: disable-error-code="list-item"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_hivemanager_ng_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    return [
        params["url"],
        params["vhm_id"],
        params["api_token"],
        params["client_id"],
        passwordstore_get_cmdline("%s", params["client_secret"]),
        params["redirect_url"],
    ]


special_agent_info["hivemanager_ng"] = agent_hivemanager_ng_arguments
