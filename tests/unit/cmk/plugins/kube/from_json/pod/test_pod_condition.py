# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.kube.from_json.pod.pod_condition import pod_condition, pod_conditions
from cmk.plugins.kube.schemata.api import ConditionType


@pytest.mark.parametrize(
    "type_str, expected_type",
    [
        ("PodScheduled", ConditionType.PODSCHEDULED),
        ("Initialized", ConditionType.INITIALIZED),
        ("ContainersReady", ConditionType.CONTAINERSREADY),
        ("Ready", ConditionType.READY),
        ("PodHasNetwork", ConditionType.PODHASNETWORK),
        ("PodReadyToStartContainers", ConditionType.PODREADYTOSTARTCONTAINERS),
        ("DisruptionTarget", ConditionType.DISRUPTIONTARGET),
        ("PodResizePending", ConditionType.PODRESIZEPENDING),
        ("PodResizeInProgress", ConditionType.PODRESIZEINPROGRESS),
    ],
)
def test_known_condition_type(type_str: str, expected_type: ConditionType) -> None:
    result = pod_condition(
        {
            "status": "True",
            "type": type_str,
            "lastTransitionTime": "2026-03-19T17:34:38Z",
        }
    )
    assert result.type == expected_type
    assert result.custom_type is None


def test_custom_condition_type() -> None:
    result = pod_condition(
        {
            "status": "False",
            "type": "SomeCustomCRDCondition",
            "lastTransitionTime": "2026-03-19T17:34:38Z",
        }
    )
    assert result.type is None
    assert result.custom_type == "SomeCustomCRDCondition"


def test_condition_message_maps_to_detail() -> None:
    result = pod_condition(
        {
            "status": "False",
            "type": "Ready",
            "reason": "ContainersNotReady",
            "message": "containers with unready status: [web]",
            "lastTransitionTime": "2026-03-19T17:34:38Z",
        }
    )
    assert result.reason == "ContainersNotReady"
    assert result.detail == "containers with unready status: [web]"


def test_condition_without_optional_fields() -> None:
    result = pod_condition(
        {
            "status": "True",
            "type": "Ready",
        }
    )
    assert result.reason is None
    assert result.detail is None
    assert result.last_transition_time is None


def test_pod_conditions_list() -> None:
    results = pod_conditions(
        [
            {"status": "True", "type": "Ready", "lastTransitionTime": "2026-03-19T17:34:38Z"},
            {
                "status": "True",
                "type": "PodScheduled",
                "lastTransitionTime": "2026-03-19T17:34:38Z",
            },
        ]
    )
    assert len(results) == 2
    assert results[0].type == ConditionType.READY
    assert results[1].type == ConditionType.PODSCHEDULED
