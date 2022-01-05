#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping, Optional

from cmk.special_agents.agent_kube import _collect_cpu_resources, Pod
from cmk.special_agents.utils_kubernetes.schemata import api, section
from cmk.special_agents.utils_kubernetes.schemata.section import ExceptionalResource


def default_pod(uid: str, attributes: Optional[Mapping[str, Any]] = None) -> Pod:
    if attributes is None:
        attributes = {}
    return Pod(
        uid=api.PodUID(uid),
        metadata=api.MetaData(name=""),
        status=api.PodStatus(
            conditions=[],
            phase=api.Phase.RUNNING,
            start_time=None,
            qos_class="burstable",
        )
        if "status" not in attributes
        else attributes["status"],
        spec=api.PodSpec(restart_policy="Always", containers=[])
        if "spec" not in attributes
        else attributes["spec"],
        containers={} if "containers" not in attributes else attributes["containers"],
    )


def test_collect_cpu_resources():
    """Test the _collect_cpu_resources aggregation function"""
    pod = default_pod(
        "POD",
        attributes={
            "spec": api.PodSpec(
                restart_policy="Always",
                containers=[
                    api.ContainerSpec(
                        name="container",
                        resources=api.ContainerResources(
                            limits=api.ResourcesRequirements(
                                cpu=0.4,
                            ),
                            requests=api.ResourcesRequirements(),
                        ),
                    )
                ],
            )
        },
    )
    assert _collect_cpu_resources([pod]) == section.Resources(
        request=ExceptionalResource.unspecified,
        limit=0.4,
    )
