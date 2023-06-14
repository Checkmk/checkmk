#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

import cmk.base.plugins.agent_based.utils.docker as docker
from cmk.base.check_api import (
    check_levels,
    discover,
    get_bytes_human_readable,
    get_parsed_item_data,
    LegacyCheckDefinition,
)
from cmk.base.config import check_info


def parse_docker_node_disk_usage(info):
    disk_usage = docker.parse_multiline(info).data
    return {r.get("type"): r for r in disk_usage if r is not None}


@get_parsed_item_data
def check_docker_node_disk_usage(_no_item, params, data):
    for key, human_readable_func in (
        ("size", get_bytes_human_readable),
        ("reclaimable", get_bytes_human_readable),
        ("count", lambda x: x),
        ("active", lambda x: x),
    ):
        value = data[key]

        yield check_levels(
            value,
            key,
            params.get(key),
            human_readable_func=human_readable_func,
            infoname=key.title(),
        )


check_info["docker_node_disk_usage"] = LegacyCheckDefinition(
    parse_function=parse_docker_node_disk_usage,
    discovery_function=discover(),
    check_function=check_docker_node_disk_usage,
    service_name="Docker disk usage - %s",
    check_ruleset_name="docker_node_disk_usage",
)
