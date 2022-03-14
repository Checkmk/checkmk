#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing as t
from itertools import product

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult
from .utils.k8s import Subset

########################################################################
# NOTE: This inv plugin (and associated special agent) is deprecated and
#       will be removed in Checkmk version 2.2.
########################################################################

#
# There will be a new concept of kubernetes services which will
# make this inventory obsolete, see CMK-2884
#


def inventory_k8s_endpoints(section: t.Sequence[Subset]) -> InventoryResult:
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.21/#endpointsubset-v1-core

    path = ["software", "applications", "kubernetes", "endpoints"]
    for subset in section:
        for address, port in product(subset.addresses, subset.ports):
            key_columns: t.Dict[str, t.Union[int, str]] = {
                "port": port.port,
                "port_name": port.name,
                "protocol": port.protocol,
                "hostname": address.hostname,
                "ip": address.ip,
            }
            if address.node_name:
                key_columns["node_name"] = address.node_name
            yield TableRow(
                path=path,
                key_columns=key_columns,
            )


register.inventory_plugin(
    name="k8s_endpoint_info",
    inventory_function=inventory_k8s_endpoints,
)
