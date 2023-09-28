#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# {
#     'port': 9000,
#     'password': 'yeah',
#     'sections': ['jvm', 'cluster_health', 'failures'],
#     'since': 30,
#     'user': 'hell',
#     'display_node_details': 'node',
#     'display_sidecar_details': 'sidecar',
#     'display_source_details': 'source',
# }


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info


def agent_graylog_arguments(
    params: Mapping[str, Any], hostname: str, ipaddress: str | None
) -> Sequence[str | tuple[str, str, str]]:
    args = [
        "-P",
        params["protocol"],
        "-m",
        ",".join(params["sections"]),
        "-t",
        params["since"],
        "-u",
        params["user"],
        "-s",
        passwordstore_get_cmdline("%s", params["password"]),
        "--display_node_details",
        params["display_node_details"],
        "--display_sidecar_details",
        params["display_sidecar_details"],
        "--display_source_details",
        params["display_source_details"],
    ]

    if "port" in params:
        args += ["-p", params["port"]]

    if "source_since" in params:
        args += ["--source_since", params["source_since"]]

    if "alerts_since" in params:
        args += ["--alerts_since", params["alerts_since"]]

    if "events_since" in params:
        args += ["--events_since", params["events_since"]]

    args.append(params["instance"])

    return args


special_agent_info["graylog"] = agent_graylog_arguments
