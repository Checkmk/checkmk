#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict

from .agent_based_api.v1.type_defs import HostLabelGenerator
from .agent_based_api.v1 import HostLabel, register

from .utils import k8s


def host_labels(section: Dict) -> HostLabelGenerator:
    if section:
        yield HostLabel(u'cmk/kubernetes_object', u'service')


register.agent_section(
    name="k8s_service_port",
    parse_function=k8s.parse_json,
    host_label_function=host_labels,
)
