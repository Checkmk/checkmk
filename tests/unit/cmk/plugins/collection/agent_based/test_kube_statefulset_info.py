#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow_untyped_defs


import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kube_statefulset_info import check_kube_statefulset_info
from cmk.plugins.kube.schemata.api import ContainerName, NamespaceName, Selector, Timestamp
from cmk.plugins.kube.schemata.section import FilteredAnnotations, StatefulSetInfo, ThinContainers


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            StatefulSetInfo(
                name="oh-lord",
                namespace=NamespaceName("have-mercy"),
                labels={},
                annotations=FilteredAnnotations({}),
                selector=Selector(match_labels={}, match_expressions=[]),
                creation_timestamp=Timestamp(1600000000.0),
                containers=ThinContainers(
                    images=frozenset({"i/name:0.5"}), names=[ContainerName("name")]
                ),
                cluster="cluster",
                kubernetes_cluster_hostname="host",
            ),
            (
                Result(state=State.OK, summary="Name: oh-lord"),
                Result(state=State.OK, summary="Namespace: have-mercy"),
                Result(state=State.OK, summary="Age: 1 second"),
            ),
            id="overall look of StatefulSet with age 1 second",
        ),
    ],
)
def test_check_kube_statefulset_info(
    section: StatefulSetInfo, expected_check_result: tuple[Result, ...]
) -> None:
    assert tuple(check_kube_statefulset_info(1600000001.0, section)) == expected_check_result
