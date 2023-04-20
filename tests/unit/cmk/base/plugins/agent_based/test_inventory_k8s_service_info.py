#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_k8s_service_info import (
    inventory_kube_service_info,
    parse_k8s_service_info,
    ServiceInfo,
)


def test_parse_k8s_service_info() -> None:
    section = parse_k8s_service_info([['{"cluster_ip": "None", "load_balance_ip": "null"}']])
    assert section.cluster_ip == "None"
    assert section.load_balance_ip == "null"


def test_inventory_k8s_service_info() -> None:
    # Assemble
    class ServiceInfoFactory(ModelFactory):
        __model__ = ServiceInfo

    section = ServiceInfoFactory.build()
    # Act
    result = list(inventory_kube_service_info(section))
    # Assert
    assert result == [
        Attributes(
            path=["software", "applications", "kubernetes", "service_info"],
            inventory_attributes={
                "cluster_ip": section.cluster_ip,
                "load_balance_ip": section.load_balance_ip,
            },
        )
    ]
