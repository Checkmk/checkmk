#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult
from .utils.k8s import parse_json

Section = Mapping[str, Mapping]

########################################################################
# NOTE: This inv plugin (and associated special agent) is deprecated and
#       will be removed in Checkmk version 2.2.
########################################################################


register.agent_section(
    name="k8s_assigned_pods",
    parse_function=parse_json,
)


def inventory_k8s_assigned_pods(section: Section) -> InventoryResult:
    path = ["software", "applications", "kubernetes", "assigned_pods"]
    for pod_name in section.get("names", []):
        # ONLY status data::little trick: key_columns and *_columns should not have common keys.
        # key_columns are used to identify a row.
        yield TableRow(
            path=path,
            key_columns={
                "id": pod_name,
            },
            inventory_columns={},
            status_columns={
                "name": pod_name,
            },
        )


register.inventory_plugin(
    name="k8s_assigned_pods",
    inventory_function=inventory_k8s_assigned_pods,
)
