#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.k8s import ClusterInfo as ClusterInfoC
from cmk.base.plugins.agent_based.utils.k8s import NodeCount as NodeCountC

from cmk.special_agents.utils_kubernetes.schemata.api import ClusterInfo as ClusterInfoA
from cmk.special_agents.utils_kubernetes.schemata.section import NodeCount as NodeCountA


def test_schemata_did_not_diverge() -> None:
    assert NodeCountA.schema() == NodeCountC.schema()
    assert ClusterInfoA.schema() == ClusterInfoC.schema()
