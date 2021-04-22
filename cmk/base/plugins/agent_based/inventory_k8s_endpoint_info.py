#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing as t
from dataclasses import dataclass
from itertools import product

from marshmallow import Schema, fields, post_load

from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .agent_based_api.v1 import register, TableRow

#
# There will be a new concept of kubernetes services which will
# make this inventory obsolete, see CMK-2884
#


@dataclass
class Address:
    hostname: str
    ip: str
    node_name: str


@dataclass
class Port:
    name: str
    port: int
    protocol: str


@dataclass
class Subset:
    addresses: t.List[Address]
    not_ready_addresses: t.List[Address]
    ports: t.List[Port]


# 2.1.0 TODO: use pydantic or marshmallow-dataclass
# and remove Schema definition.
class AddressSchema(Schema):
    hostname = fields.Str()
    ip = fields.Str()
    node_name = fields.Str()

    @post_load
    def make_object(self, data, **kwargs):
        return Address(**data)


class PortSchema(Schema):
    name = fields.Str()
    port = fields.Integer()
    protocol = fields.Str()

    @post_load
    def make_object(self, data, **kwargs):
        return Port(**data)


class SubsetSchema(Schema):
    addresses = fields.List(fields.Nested(AddressSchema))
    not_ready_addresses = fields.List(fields.Nested(AddressSchema))
    ports = fields.List(fields.Nested(PortSchema))

    @post_load
    def make_object(self, data, **kwargs):
        return Subset(**data)


class SubsetsSchema(Schema):
    subsets = fields.List(fields.Nested(SubsetSchema))

    @post_load
    def make_object(self, data, **kwargs) -> t.Sequence[Subset]:
        return data['subsets']


def parse_k8s_endpoint_info(string_table: StringTable) -> t.Sequence[Subset]:
    return SubsetsSchema().loads(string_table[0][0])


register.agent_section(
    name="k8s_endpoint_info",
    parse_function=parse_k8s_endpoint_info,
)


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
