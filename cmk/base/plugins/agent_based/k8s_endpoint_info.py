#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Sequence

from marshmallow import fields, post_load, Schema

from .agent_based_api.v1 import HostLabel, register
from .agent_based_api.v1.type_defs import HostLabelGenerator, StringTable
from .utils import k8s
from .utils.k8s import Address, Port, Subset

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


def host_labels(section: Sequence[k8s.Subset]) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/kubernetes_object:endpoint :
            This label indicates that this host is a endpoint object of
            kubernetes.

        cmk/kubernetes :
            This label is set to "yes" for all Kubernetes objects.

    """
    # always return host labels, even if section is empty.
    # 1) empty endpoints are valid
    # 2) the host object is already created, so we need to attach the
    #    cmk/kubernetes:yes label
    yield HostLabel("cmk/kubernetes_object", "endpoint")
    yield HostLabel("cmk/kubernetes", "yes")


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
    def make_object(self, data, **kwargs) -> Sequence[k8s.Subset]:
        return data["subsets"]


def parse_k8s_endpoint_info(string_table: StringTable) -> Sequence[k8s.Subset]:
    return SubsetsSchema().loads(string_table[0][0])


register.agent_section(
    name="k8s_endpoint_info",
    parse_function=parse_k8s_endpoint_info,
    host_label_function=host_labels,
)
