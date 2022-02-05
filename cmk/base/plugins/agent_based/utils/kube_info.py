#!/usr/bin/env python3
# -*- coding: utf-8 -*
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Callable, Literal, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import render, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils.k8s import CreationTimestamp


def result_simple(display_name: str, notice_only=False):
    key = "notice" if notice_only else "summary"

    def result_func(value):
        return Result(state=State.OK, **{key: f"{display_name}: {value}"})

    return result_func


def result_from_age(value: CreationTimestamp) -> Result:
    return Result(
        state=State.OK,
        summary=f"Age: {render.timespan(time.time() - value)}",
    )


InfoTypes = Literal[
    "name",
    "node",
    "namespace",
    "os_image",
    "container_runtime_version",
    "creation_timestamp",
    "qos_class",
    "uid",
    "restart_policy",
    "architecture",
    "kernel_version",
    "operating_system",
]

_RESULT_FUNC: Mapping[InfoTypes, Callable[[Any], Result]] = {
    "name": result_simple("Name"),
    "node": result_simple("Node"),
    "namespace": result_simple("Namespace"),
    "creation_timestamp": result_from_age,
    "os_image": result_simple("OS"),
    "container_runtime_version": result_simple("Container runtime"),
    "qos_class": result_simple("QoS class", notice_only=True),
    "uid": result_simple("UID", notice_only=True),
    "restart_policy": result_simple("Restart policy", notice_only=True),
    "architecture": result_simple("Architecture", notice_only=True),
    "kernel_version": result_simple("Kernel version", notice_only=True),
    "operating_system": result_simple("OS family", notice_only=True),
}


def check_info(info: Mapping[InfoTypes, Any]) -> CheckResult:
    for info_type, function in _RESULT_FUNC.items():
        if info_type in info:
            yield function(info[info_type])
