#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow_untyped_defs


from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kube_namespace_info import check_kube_namespace_info
from cmk.plugins.kube.schemata.api import NamespaceName, Timestamp
from cmk.plugins.kube.schemata.section import FilteredAnnotations, NamespaceInfo


def test_check_kube_namespace_info() -> None:
    info = NamespaceInfo(
        name=NamespaceName("namespace"),
        creation_timestamp=Timestamp(1600000000.0),
        labels={},
        annotations=FilteredAnnotations({}),
        cluster="cluster",
        kubernetes_cluster_hostname="host",
    )
    check_result = check_kube_namespace_info(1600000001.0, info)
    assert list(check_result) == [
        Result(state=State.OK, summary="Name: namespace"),
        Result(state=State.OK, summary="Age: 1 second"),
    ]
