#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.base.config import special_agent_info


def agent_acme_sbc(
    params: Mapping[str, object], hostname: str, ipaddress: str | None
) -> Sequence[str]:
    return [hostname]


special_agent_info["acme_sbc"] = agent_acme_sbc
