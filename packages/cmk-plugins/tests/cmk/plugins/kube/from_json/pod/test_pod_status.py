# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="typeddict-item"

import pytest

from cmk.plugins.kube.from_json.pod.pod_status import pod_status
from cmk.plugins.kube.schemata.api import IpAddress, Phase


@pytest.mark.parametrize(
    "phase_str, expected",
    [
        ("Running", Phase.RUNNING),
        ("Pending", Phase.PENDING),
        ("Succeeded", Phase.SUCCEEDED),
        ("Failed", Phase.FAILED),
        ("Unknown", Phase.UNKNOWN),
    ],
)
def test_phase_parsing(phase_str: str, expected: Phase) -> None:
    result = pod_status({"phase": phase_str})
    assert result.phase == expected
    assert result.conditions is None
    assert result.start_time is None
    assert result.host_ip is None
    assert result.pod_ip is None
    assert result.qos_class is None


def test_full_status() -> None:
    result = pod_status(
        {
            "phase": "Running",
            "startTime": "2026-03-19T17:34:38Z",
            "hostIP": "172.18.0.2",
            "podIP": "10.244.1.14",
            "qosClass": "Burstable",
            "conditions": [
                {"status": "True", "type": "Ready", "lastTransitionTime": "2026-03-19T17:34:50Z"},
            ],
        }
    )
    assert result.host_ip == IpAddress("172.18.0.2")
    assert result.pod_ip == IpAddress("10.244.1.14")
    assert result.qos_class == "burstable"
    assert result.conditions is not None
    assert len(result.conditions) == 1


@pytest.mark.parametrize(
    "raw_qos, expected",
    [
        ("Burstable", "burstable"),
        ("BestEffort", "besteffort"),
        ("Guaranteed", "guaranteed"),
    ],
)
def test_qos_class_lowercased(raw_qos: str, expected: str) -> None:
    result = pod_status({"phase": "Running", "qosClass": raw_qos})
    assert result.qos_class == expected


def test_qos_class_unknown_value_becomes_none() -> None:
    result = pod_status({"phase": "Running", "qosClass": "SomethingNew"})
    assert result.qos_class is None
