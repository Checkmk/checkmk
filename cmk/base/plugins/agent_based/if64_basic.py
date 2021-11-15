#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Mapping

from .agent_based_api.v1 import register, type_defs
from .utils import interfaces


def check_interfaces(
    item: str,
    params: Mapping[str, Any],
    section: interfaces.Section,
) -> type_defs.CheckResult:
    yield from interfaces.check_multiple_interfaces(
        item=item,
        params=params,
        section=section,
        group_name="Interface group",
        timestamp=time.time(),
        input_is_rate=False,
    )


register.check_plugin(
    name="interfaces",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_interfaces,
    cluster_check_function=interfaces.cluster_check,
)
