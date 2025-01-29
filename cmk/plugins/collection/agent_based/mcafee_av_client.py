#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)


def parse_mcafee_av_client(string_table: StringTable) -> float:
    """
    Section:
      # <<<mcafee_av_client>>>
      # 2015/05/06

    >>> timestamp = parse_mcafee_av_client([
    ...     ['2015/05/06'],
    ... ])
    >>> 1400000000.0 < timestamp < 1500000000.0  # exact value is timezone dependent
    True
    """
    # We assume that the timestamp is to be interpreted in the timezone of
    # the Checkmk server. This might be a problem, if e.g. the agent is located
    # in China and the Checkmk server in USA.
    return time.mktime(time.strptime(string_table[0][0], "%Y/%m/%d"))


agent_section_mcafee_av_client = AgentSection(
    name="mcafee_av_client",
    parse_function=parse_mcafee_av_client,
)


def discover_mcafee_av_client(section: float) -> DiscoveryResult:
    yield Service()


def check_mcafee_av_client(params: Mapping[str, Any], section: float) -> CheckResult:
    yield from check_levels_v1(
        time.time() - section,
        levels_upper=params.get("signature_age"),
        render_func=render.timespan,
        label="Time since last update of signatures",
    )


check_plugin_mcafee_av_client = CheckPlugin(
    name="mcafee_av_client",
    service_name="McAfee AV",
    discovery_function=discover_mcafee_av_client,
    check_function=check_mcafee_av_client,
    check_ruleset_name="mcafee_av_client",
    check_default_parameters={
        "signature_age": (86400, 7 * 86400),
    },
)
