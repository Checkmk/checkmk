#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def _has_piggyback_services(params):
    return len(params.get("piggyback", {}).get("piggyback_services", [])) > 0


def agent_gcp_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str | tuple[str, str, str]]:
    today = datetime.date.today()
    args = [
        "--project",
        params["project"],
        "--credentials",
        passwordstore_get_cmdline("%s", params["credentials"]),
        "--date",
        today.isoformat(),
    ]
    if "cost" in params:
        args.append("--cost_table")
        args.append(params["cost"]["tableid"])
    if len(params["services"]) > 0 or _has_piggyback_services(params):
        args.append("--services")
    if len(params["services"]) > 0:
        args.extend(params["services"])
    if _has_piggyback_services(params):
        args.extend(params["piggyback"]["piggyback_services"])

    args.append("--piggy-back-prefix")
    if "prefix" in params.get("piggyback", {}):
        args.append(params["piggyback"]["prefix"])
    else:
        args.append(params["project"])

    return args


special_agent_info["gcp"] = agent_gcp_arguments
