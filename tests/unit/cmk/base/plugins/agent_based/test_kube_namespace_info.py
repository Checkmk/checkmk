#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_namespace_info import check_kube_namespace_info
from cmk.base.plugins.agent_based.utils import kube_info
from cmk.base.plugins.agent_based.utils.kube import NamespaceInfo


def test_check_kube_namespace_info(mocker) -> None:  # type:ignore[no-untyped-def]
    info = NamespaceInfo(
        name="namespace",
        creation_timestamp=1600000000.0,
        labels={},
        annotations={},
        cluster="cluster",
    )
    with mocker.patch.object(kube_info.time, "time", return_value=1600000001.0):
        check_result = check_kube_namespace_info(info)
    assert list(check_result) == [
        Result(state=State.OK, summary="Name: namespace"),
        Result(state=State.OK, summary="Age: 1 second"),
    ]
