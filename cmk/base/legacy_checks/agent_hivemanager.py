#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

from typing import Optional, Sequence

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_hivemanager_arguments(
    params: tuple, hostname: str, ipaddress: Optional[str]
) -> Sequence[str]:
    # User, Password
    return [ipaddress or hostname, params[0], passwordstore_get_cmdline("%s", params[1])]


special_agent_info["hivemanager"] = agent_hivemanager_arguments
