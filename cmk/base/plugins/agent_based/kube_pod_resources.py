#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .utils.kube_pod_resources import (
    _DEFAULT_PARAMS,
    check_kube_pod_resources,
    discovery_kube_pod_resources,
    parse_kube_pod_resources,
)

register.agent_section(
    name="kube_pod_resources_v1",
    parse_function=parse_kube_pod_resources,
    parsed_section_name="kube_pod_resources",
)

register.check_plugin(
    name="kube_pod_resources",
    service_name="Pod Resources",
    discovery_function=discovery_kube_pod_resources,
    check_function=check_kube_pod_resources,
    check_default_parameters=_DEFAULT_PARAMS,
    check_ruleset_name="kube_pod_resources",
)
