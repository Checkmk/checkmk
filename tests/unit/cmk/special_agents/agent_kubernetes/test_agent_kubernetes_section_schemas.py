#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.k8s import ClusterInfo as ClusterInfoC
from cmk.base.plugins.agent_based.utils.k8s import ContainerCount as ContainerCountC
from cmk.base.plugins.agent_based.utils.k8s import KubeletInfo as KubeletInfoC
from cmk.base.plugins.agent_based.utils.k8s import Memory as MemoryC
from cmk.base.plugins.agent_based.utils.k8s import NodeCount as NodeCountC
from cmk.base.plugins.agent_based.utils.k8s import PodResources as PodResourcesC
from cmk.base.plugins.agent_based.utils.k8s import (
    PodResourcesWithCapacity as PodResourcesWithCapacityC,
)
from cmk.base.plugins.agent_based.utils.k8s import Resources as ResourcesC
from cmk.base.plugins.agent_based.utils.k8s import StartTime as StartTimeC

from cmk.special_agents.utils_kubernetes.schemata.api import ClusterInfo as ClusterInfoA
from cmk.special_agents.utils_kubernetes.schemata.api import KubeletInfo as KubeletInfoA
from cmk.special_agents.utils_kubernetes.schemata.api import Resources as ResourcesA
from cmk.special_agents.utils_kubernetes.schemata.api import StartTime as StartTimeA
from cmk.special_agents.utils_kubernetes.schemata.section import ContainerCount as ContainerCountA
from cmk.special_agents.utils_kubernetes.schemata.section import Memory as MemoryA
from cmk.special_agents.utils_kubernetes.schemata.section import NodeCount as NodeCountA
from cmk.special_agents.utils_kubernetes.schemata.section import PodResources as PodResourcesA
from cmk.special_agents.utils_kubernetes.schemata.section import (
    PodResourcesWithCapacity as PodResourcesWithCapacityA,
)


def test_schemata_did_not_diverge() -> None:
    assert ClusterInfoA.schema() == ClusterInfoC.schema()
    assert ContainerCountA.schema() == ContainerCountC.schema()
    assert KubeletInfoA.schema() == KubeletInfoC.schema()
    assert MemoryC.schema() == MemoryA.schema()
    assert NodeCountA.schema() == NodeCountC.schema()
    assert PodResourcesA.schema() == PodResourcesC.schema()
    assert PodResourcesWithCapacityA.schema() == PodResourcesWithCapacityC.schema()
    assert ResourcesA.schema() == ResourcesC.schema()
    assert StartTimeA.schema() == StartTimeC.schema()
