#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Dict,)
from itertools import zip_longest
from .utils import docker

from .agent_based_api.v1.type_defs import (
    StringTable,
    HostLabelGenerator,
)

from .agent_based_api.v1 import (
    register,
    HostLabel,
)

Section = Dict


def parse_docker_node_info(string_table: StringTable) -> Section:
    loaded: Section = {}
    # docker_node_info section may be present multiple times,
    # this is how the docker agent plugin reports errors.
    # Key 'Unknown' is present if there is a python exception
    # key 'Critical' is present if the python docker lib is not found
    string_table_iter = iter(string_table)
    for local_string_table in zip_longest(string_table_iter, string_table_iter):
        # local_string_table holds two consecutive elements of string_table.
        # first loop: [string_table[0], string_table[1]]
        # second loop: [string_table[1], string_table[2]]
        # etc
        parsed = docker.parse(local_string_table).data
        loaded.update(parsed)
    return loaded


def host_labels_docker_node_info(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/docker_object:node :
            This Label is set, if the corresponding host is a docker node.

    """
    if section:
        yield HostLabel(u"cmk/docker_object", u"node")


register.agent_section(
    name="docker_node_info",
    parse_function=parse_docker_node_info,
    host_label_function=host_labels_docker_node_info,
)
