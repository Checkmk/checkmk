#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import StatefulSetInfo
from cmk.base.plugins.agent_based.utils.kube_info import check_info, host_labels


def parse(string_table: StringTable) -> StatefulSetInfo:
    """Parses `string_table` into a StatefulSetInfo instance

    >>> parse([[
    ... '{"name": "oh-lord",'
    ... '"namespace": "have-mercy",'
    ... '"labels": {},'
    ... '"selector": {"match_labels": {}, "match_expressions": [{"key": "app", "operator": "In", "values": ["sleep"]}]},'
    ... '"creation_timestamp": 1638798546.0,'
    ... '"containers": {"images": ["i/name:0.5"], "names": ["name"]},'
    ... '"cluster": "sweet-jesus"}'
    ... ]])
    StatefulSetInfo(name='oh-lord', namespace='have-mercy', labels={}, selector=Selector(match_labels={}, match_expressions=[{'key': 'app', 'operator': 'In', 'values': ['sleep']}]), creation_timestamp=1638798546.0, containers=ThinContainers(images=frozenset({'i/name:0.5'}), names=['name']), cluster='sweet-jesus')
    """
    return StatefulSetInfo(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_statefulset_info_v1",
    parsed_section_name="kube_statefulset_info",
    parse_function=parse,
    host_label_function=host_labels("statefulset"),
)


def discovery(section: StatefulSetInfo) -> DiscoveryResult:
    yield Service()


def check_kube_statefulset_info(section: StatefulSetInfo) -> CheckResult:
    yield from check_info(
        {
            "name": section.name,
            "namespace": section.namespace,
            "creation_timestamp": section.creation_timestamp,
        }
    )


register.check_plugin(
    name="kube_statefulset_info",
    service_name="Info",
    discovery_function=discovery,
    check_function=check_kube_statefulset_info,
)
