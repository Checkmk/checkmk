#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing as t

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult

########################################################################
# NOTE: This inv plugin (and associated special agent) is deprecated and
#       will be removed in Checkmk version 2.2.
########################################################################

#
# There will be a new concept of kubernetes services which will
# make this inventory obsolete, see CMK-2884
#


def inventory_k8s_ingress_info(section: t.Any) -> InventoryResult:
    path = ["software", "applications", "kubernetes", "ingresses"]
    for name, data in section.items():
        for service_path, service_name, service_port in data["backends"]:
            yield TableRow(
                path=path + [name, "backends"],
                key_columns={
                    "path": service_path,
                    "service_name": service_name,
                    "service_port": service_port,
                },
            )

        for secret_name, hosts in data["hosts"].items():
            for host in hosts:
                yield TableRow(
                    path=path + [name, "hosts"],
                    key_columns={
                        "host": host,
                        "secret_name": secret_name,
                    },
                )

        for load_balancer in data["load_balancers"]:
            yield TableRow(
                path=path + [name, "load_balancers"],
                key_columns=load_balancer,
            )


register.inventory_plugin(
    name="k8s_ingress_infos",
    inventory_function=inventory_k8s_ingress_info,
)
