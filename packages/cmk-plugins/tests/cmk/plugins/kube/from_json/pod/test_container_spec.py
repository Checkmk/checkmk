# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="typeddict-item"

import pytest

from cmk.plugins.kube.from_json.pod.container_spec import (
    container_resources,
    containers_spec,
)
from cmk.plugins.kube.schemata.api import ContainerName


@pytest.mark.parametrize(
    "resources, expected_limits_memory, expected_limits_cpu, expected_requests_memory, expected_requests_cpu",
    [
        pytest.param(
            {"requests": {"cpu": "150m", "memory": "200Mi"}},
            None,
            None,
            200 * 1024**2,
            0.15,
            id="requests only",
        ),
        pytest.param(
            {
                "limits": {"cpu": "1", "memory": "1Gi"},
                "requests": {"cpu": "500m", "memory": "512Mi"},
            },
            1024**3,
            1.0,
            512 * 1024**2,
            0.5,
            id="limits and requests",
        ),
        pytest.param(
            {},
            None,
            None,
            None,
            None,
            id="empty resources",
        ),
    ],
)
def test_container_resources(
    resources: dict[str, object],
    expected_limits_memory: float | None,
    expected_limits_cpu: float | None,
    expected_requests_memory: float | None,
    expected_requests_cpu: float | None,
) -> None:
    result = container_resources(
        {"name": "test", "imagePullPolicy": "Always", "resources": resources}
    )
    assert result.limits.memory == expected_limits_memory
    assert result.limits.cpu == expected_limits_cpu
    assert result.requests.memory == expected_requests_memory
    assert result.requests.cpu == expected_requests_cpu


def test_container_resources_no_resources_key() -> None:
    result = container_resources({"name": "test", "imagePullPolicy": "Always"})
    assert result.limits.memory is None
    assert result.limits.cpu is None
    assert result.requests.memory is None
    assert result.requests.cpu is None


def test_containers_spec() -> None:
    result = containers_spec(
        [
            {"name": "web", "imagePullPolicy": "Always"},
            {"name": "sidecar", "imagePullPolicy": "IfNotPresent"},
        ]
    )
    assert len(result) == 2
    assert result[0].name == ContainerName("web")
    assert result[0].image_pull_policy == "Always"
    assert result[1].name == ContainerName("sidecar")
    assert result[1].image_pull_policy == "IfNotPresent"
