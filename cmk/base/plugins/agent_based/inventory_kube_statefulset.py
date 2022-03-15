#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable
from cmk.base.plugins.agent_based.utils.kube import StatefulSetInfo, StatefulSetStrategy
from cmk.base.plugins.agent_based.utils.kube_inventory import (
    labels_to_table,
    match_expressions_to_str,
    match_labels_to_str,
)
from cmk.base.plugins.agent_based.utils.kube_strategy import statefulset_strategy_text


def parse_kube_statefulset_strategy(string_table: StringTable) -> StatefulSetStrategy:
    """
    >>> parse_kube_statefulset_strategy([['{"strategy": {"type_": "OnDelete"}}']])
    StatefulSetStrategy(strategy=OnDelete(type_='OnDelete'))
    >>> parse_kube_statefulset_strategy([['{"strategy": {"type_": "RollingUpdate", "partition": 0}}']])
    StatefulSetStrategy(strategy=StatefulSetRollingUpdate(type_='RollingUpdate', partition=0))
    """

    return StatefulSetStrategy(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_statefulset_strategy_v1",
    parsed_section_name="kube_statefulset_strategy",
    parse_function=parse_kube_statefulset_strategy,
)


def inventory_kube_statefulset(
    section_kube_statefulset_info: Optional[StatefulSetInfo],
    section_kube_statefulset_strategy: Optional[StatefulSetStrategy],
) -> InventoryResult:
    if section_kube_statefulset_info is None or section_kube_statefulset_strategy is None:
        return
    selector = section_kube_statefulset_info.selector
    yield Attributes(
        path=["software", "applications", "kube", "statefulset"],
        inventory_attributes={
            "name": section_kube_statefulset_info.name,
            "namespace": section_kube_statefulset_info.namespace,
            "strategy": statefulset_strategy_text(section_kube_statefulset_strategy.strategy),
            "match_labels": match_labels_to_str(selector.match_labels),
            "match_expressions": match_expressions_to_str(selector.match_expressions),
        },
    )
    yield from labels_to_table(section_kube_statefulset_info.labels)


register.inventory_plugin(
    name="kube_statefulset",
    sections=["kube_statefulset_info", "kube_statefulset_strategy"],
    inventory_function=inventory_kube_statefulset,
)
