#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from typing import Any, Mapping, Sequence

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult
from .utils.k8s import parse_json

Section = Mapping[str, Sequence[Mapping[str, Any]]]

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


register.agent_section(
    name="k8s_roles",
    parse_function=parse_json,
)


def inventory_k8s_roles(section: Section) -> InventoryResult:
    for role in sorted(
        itertools.chain(section["cluster_roles"], section["roles"]),
        key=lambda x: x["name"],
    ):
        yield TableRow(
            path=["software", "applications", "kubernetes", "roles"],
            key_columns={
                "role": role["name"],
            },
            inventory_columns={
                "namespace": role["namespace"],
            },
            status_columns={},
        )


register.inventory_plugin(
    name="k8s_roles",
    inventory_function=inventory_k8s_roles,
)
