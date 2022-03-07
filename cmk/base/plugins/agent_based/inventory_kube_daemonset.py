#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult, StringTable
from cmk.base.plugins.agent_based.utils.k8s import DaemonSetInfo, DaemonSetStrategy
from cmk.base.plugins.agent_based.utils.kube_inventory import (
    match_expressions_to_str,
    match_labels_to_str,
)
from cmk.base.plugins.agent_based.utils.kube_strategy import strategy_text


def parse_kube_daemonset_strategy(string_table: StringTable) -> DaemonSetStrategy:
    return DaemonSetStrategy(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_daemonset_strategy_v1",
    parsed_section_name="kube_daemonset_strategy",
    parse_function=parse_kube_daemonset_strategy,
)


def inventory_kube_daemonset(
    section_kube_daemonset_info: Optional[DaemonSetInfo],
    section_kube_daemonset_strategy: Optional[DaemonSetStrategy],
) -> InventoryResult:
    if section_kube_daemonset_info is None or section_kube_daemonset_strategy is None:
        return
    selector = section_kube_daemonset_info.selector
    yield Attributes(
        path=["software", "applications", "kube", "daemonset"],
        inventory_attributes={
            "name": section_kube_daemonset_info.name,
            "namespace": section_kube_daemonset_info.namespace,
            "strategy": strategy_text(section_kube_daemonset_strategy.strategy),
            "match_labels": match_labels_to_str(selector.match_labels),
            "match_expressions": match_expressions_to_str(selector.match_expressions),
        },
    )
    for label in section_kube_daemonset_info.labels.values():
        yield TableRow(
            path=["software", "applications", "kube", "labels"],
            key_columns={"label_name": label.name},
            inventory_columns={"label_value": label.value},
        )


register.inventory_plugin(
    name="kube_daemonset",
    sections=["kube_daemonset_info", "kube_daemonset_strategy"],
    inventory_function=inventory_kube_daemonset,
)
