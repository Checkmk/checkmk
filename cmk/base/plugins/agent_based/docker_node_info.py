#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Dict,)
from .utils import docker, legacy_docker

from .agent_based_api.v1.type_defs import (
    StringTable,
    HostLabelGenerator,
)

from .agent_based_api.v1 import (
    register,
    HostLabel,
)

Section = Dict  # either dict, or the inherited class to indicate legacy agent plugin


def parse_docker_node_info(string_table: StringTable) -> Section:
    version = docker.get_version(string_table)
    if version is None:
        return legacy_docker.parse_node_info(string_table)

    if len(string_table) < 2:
        return {}

    loaded: Section = {}
    for line in string_table[1:]:
        loaded.update(docker.json_get_obj(line) or {})
    return loaded


def host_labels_docker_node_info(section: Section) -> HostLabelGenerator:
    if section:
        yield HostLabel(u"cmk/docker_object", u"node")


register.agent_section(
    name="docker_node_info",
    parse_function=parse_docker_node_info,
    host_label_function=host_labels_docker_node_info,
)
