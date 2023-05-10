# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=name-defined
# pylint: disable=undefined-variable

import os

for _h in os.listdir(f"{os.getenv('OMD_ROOT')}/var/check_mk/agent_output"):
    if _h[0] == ".":
        continue
    all_hosts.append(_h + "|tcp|wato|/wato/agents/")
    ipaddresses[_h] = "127.0.0.1"
    host_attributes[_h] = {
        "ipaddress": "127.0.0.1",
        "tag_agent": "cmk-agent",
    }
