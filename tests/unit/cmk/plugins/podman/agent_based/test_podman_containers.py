#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.podman.agent_based.podman_containers import (
    check_podman_containers,
    DEFAULT_PARAMS,
    discover_podman_containers,
    Params,
    parse_podman_containers,
)

_STRING_TABLE_ALL_RUNNING = [
    [
        '[{"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-05-23T14:54:02.637183731+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 0, "Id": "50baa2b53cb3548c717526bd80eca26e5d525f3f7a2479f06f3eab88d5332053", "Image": "localhost/rootful-container:latest", "ImageID": "b94a67d30b3c46916d36bda349ecc9bdef11ff9c90bb55e514575488c3726617", "IsInfra": false, "Labels": {"io.buildah.version": "1.33.7"}, "Mounts": [], "Names": ["root"], "Namespaces": {}, "Networks": ["podman"], "Pid": 31897, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1751555516, "State": "running", "Status": ""}]'
    ],
    [
        '[{"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-06-30T17:22:38.117310829+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 0, "Id": "63f10448c71cd61479ed6edf515bf45486f2e3b0008f873920ecc2c9008e7276", "Image": "localhost/rootless-container:latest", "ImageID": "e40e7fb7eb39f4ff4f7d1e43b3a6c193426a7597c8a8c4d477a974a2804eae10", "IsInfra": false, "Labels": {"io.buildah.version": "1.33.7"}, "Mounts": [], "Names": ["nonroot-test"], "Namespaces": {}, "Networks": [], "Pid": 47643, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1752407468, "State": "running", "Status": ""}]'
    ],
]
_STRING_TABLE_ONE_DEAD = [
    [
        '[{"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-05-23T14:54:02.637183731+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 0, "Id": "50baa2b53cb3548c717526bd80eca26e5d525f3f7a2479f06f3eab88d5332053", "Image": "localhost/rootful-container:latest", "ImageID": "b94a67d30b3c46916d36bda349ecc9bdef11ff9c90bb55e514575488c3726617", "IsInfra": false, "Labels": {"io.buildah.version": "1.33.7"}, "Mounts": [], "Names": ["root"], "Namespaces": {}, "Networks": ["podman"], "Pid": 31897, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1751555516, "State": "running", "Status": ""}, {"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-06-13T15:22:15.64265355+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 0, "Id": "c276a7fa9de6c2190bdcb32282bef077de8943c6c513d6ef065c869fc26aadef", "Image": "localhost/rootful-container:latest", "ImageID": "b94a67d30b3c46916d36bda349ecc9bdef11ff9c90bb55e514575488c3726617", "IsInfra": false, "Labels": {"io.buildah.version": "1.33.7"}, "Mounts": [], "Names": ["roott"], "Namespaces": {}, "Networks": ["podman"], "Pid": 31846, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1751555515, "State": "running", "Status": ""}]'
    ],
    [
        '[{"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-06-30T17:22:38.117310829+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 0, "Id": "63f10448c71cd61479ed6edf515bf45486f2e3b0008f873920ecc2c9008e7276", "Image": "localhost/rootless-container:latest", "ImageID": "e40e7fb7eb39f4ff4f7d1e43b3a6c193426a7597c8a8c4d477a974a2804eae10", "IsInfra": false, "Labels": null, "Mounts": [], "Names": ["nonroot-test"], "Namespaces": {}, "Networks": [], "Pid": 47643, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1752407468, "State": "dead", "Status": ""}]'
    ],
]
_STRING_TABLE_TWO_EXITED_NON_ZERO = [
    [
        '[{"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-05-23T14:54:02.637183731+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 1, "Id": "50baa2b53cb3548c717526bd80eca26e5d525f3f7a2479f06f3eab88d5332053", "Image": "localhost/rootful-container:latest", "ImageID": "b94a67d30b3c46916d36bda349ecc9bdef11ff9c90bb55e514575488c3726617", "IsInfra": false, "Labels": {"io.buildah.version": "1.33.7"}, "Mounts": [], "Names": ["root"], "Namespaces": {}, "Networks": ["podman"], "Pid": 31897, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1751555516, "State": "running", "Status": ""}, {"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-06-13T15:22:15.64265355+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 0, "Id": "c276a7fa9de6c2190bdcb32282bef077de8943c6c513d6ef065c869fc26aadef", "Image": "localhost/rootful-container:latest", "ImageID": "b94a67d30b3c46916d36bda349ecc9bdef11ff9c90bb55e514575488c3726617", "IsInfra": false, "Labels": {"io.buildah.version": "1.33.7"}, "Mounts": [], "Names": ["roott"], "Namespaces": {}, "Networks": ["podman"], "Pid": 31846, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1751555515, "State": "running", "Status": ""}]'
    ],
    [
        '[{"AutoRemove": false, "Command": ["sleep", "infinity"], "Created": "2025-06-30T17:22:38.117310829+02:00", "CreatedAt": "", "CIDFile": "", "Exited": false, "ExitedAt": -62135596800, "ExitCode": 1, "Id": "63f10448c71cd61479ed6edf515bf45486f2e3b0008f873920ecc2c9008e7276", "Image": "localhost/rootless-container:latest", "ImageID": "e40e7fb7eb39f4ff4f7d1e43b3a6c193426a7597c8a8c4d477a974a2804eae10", "IsInfra": false, "Labels": {"io.buildah.version": "1.33.7"}, "Mounts": [], "Names": ["nonroot-test"], "Namespaces": {}, "Networks": [], "Pid": 47643, "Pod": "", "PodName": "", "Ports": null, "Restarts": 0, "Size": null, "StartedAt": 1752407468, "State": "paused", "Status": ""}]'
    ],
]


def test_discover_podman_containers():
    assert list(discover_podman_containers(parse_podman_containers(_STRING_TABLE_ALL_RUNNING))) == [
        Service()
    ]
    assert list(discover_podman_containers(parse_podman_containers([[]]))) == [Service()]


@pytest.mark.parametrize(
    "string_table, params, expected_result",
    [
        pytest.param(
            _STRING_TABLE_ALL_RUNNING,
            DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Total: 2"),
                Metric("podman_containers_total_number", 2.0),
                Result(state=State.OK, summary="Running: 2"),
                Metric("podman_containers_running_number", 2.0, boundaries=(0.0, 2.0)),
                Result(state=State.OK, summary="Created: 0"),
                Metric("podman_containers_created_number", 0.0),
                Result(state=State.OK, summary="Paused: 0"),
                Metric("podman_containers_paused_number", 0.0),
                Result(state=State.OK, summary="Stopped: 0"),
                Metric("podman_containers_stopped_number", 0.0),
                Result(state=State.OK, notice="Restarting: 0"),
                Metric("podman_containers_restarting_number", 0.0),
                Result(state=State.OK, notice="Removing: 0"),
                Metric("podman_containers_removing_number", 0.0),
                Result(state=State.OK, notice="Dead: 0"),
                Metric("podman_containers_dead_number", 0.0, levels=(1.0, 1.0)),
                Result(state=State.OK, summary="Exited: 0"),
                Metric("podman_containers_exited_number", 0.0),
                Result(state=State.OK, notice="Exited as non zero: 0"),
                Metric("podman_containers_exited_as_non_zero_number", 0.0, levels=(1.0, 1.0)),
            ],
            id="All running containers -> OK",
        ),
        pytest.param(
            _STRING_TABLE_ONE_DEAD,
            DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Total: 3"),
                Metric("podman_containers_total_number", 3.0),
                Result(state=State.OK, summary="Running: 2"),
                Metric("podman_containers_running_number", 2.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Created: 0"),
                Metric("podman_containers_created_number", 0.0),
                Result(state=State.OK, summary="Paused: 0"),
                Metric("podman_containers_paused_number", 0.0),
                Result(state=State.OK, summary="Stopped: 0"),
                Metric("podman_containers_stopped_number", 0.0),
                Result(state=State.OK, notice="Restarting: 0"),
                Metric("podman_containers_restarting_number", 0.0),
                Result(state=State.OK, notice="Removing: 0"),
                Metric("podman_containers_removing_number", 0.0),
                Result(state=State.CRIT, notice="Dead: 1 (warn/crit at 1/1)"),
                Metric("podman_containers_dead_number", 1.0, levels=(1.0, 1.0)),
                Result(state=State.OK, summary="Exited: 0"),
                Metric("podman_containers_exited_number", 0.0),
                Result(state=State.OK, notice="Exited as non zero: 0"),
                Metric("podman_containers_exited_as_non_zero_number", 0.0, levels=(1.0, 1.0)),
            ],
            id="Two running containers, one dead -> CRIT",
        ),
        pytest.param(
            _STRING_TABLE_TWO_EXITED_NON_ZERO,
            {
                "paused": {"levels_upper": ("fixed", (1, 1))},
                "stopped": {"levels_upper": ("fixed", (1, 1))},
                "dead": {"levels_upper": ("fixed", (1, 1))},
                "exited_as_non_zero": {"levels_upper": ("fixed", (2, 3))},
            },
            [
                Result(state=State.OK, summary="Total: 3"),
                Metric("podman_containers_total_number", 3.0),
                Result(state=State.OK, summary="Running: 2"),
                Metric("podman_containers_running_number", 2.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Created: 0"),
                Metric("podman_containers_created_number", 0.0),
                Result(state=State.CRIT, summary="Paused: 1 (warn/crit at 1/1)"),
                Metric("podman_containers_paused_number", 1.0, levels=(1.0, 1.0)),
                Result(state=State.OK, summary="Stopped: 0"),
                Metric("podman_containers_stopped_number", 0.0, levels=(1.0, 1.0)),
                Result(state=State.OK, notice="Restarting: 0"),
                Metric("podman_containers_restarting_number", 0.0),
                Result(state=State.OK, notice="Removing: 0"),
                Metric("podman_containers_removing_number", 0.0),
                Result(state=State.OK, notice="Dead: 0"),
                Metric("podman_containers_dead_number", 0.0, levels=(1.0, 1.0)),
                Result(state=State.OK, summary="Exited: 0"),
                Metric("podman_containers_exited_number", 0.0),
                Result(state=State.WARN, notice="Exited as non zero: 2 (warn/crit at 2/3)"),
                Metric("podman_containers_exited_as_non_zero_number", 2.0, levels=(2.0, 3.0)),
            ],
            id="Two exited non-zero containers, one running - custom thresholds -> WARN",
        ),
        pytest.param(
            [[]],
            {},
            [
                Result(state=State.OK, summary="No containers found"),
            ],
            id="No containers -> OK",
        ),
    ],
)
def test_check_podman_containers(
    string_table: StringTable, params: Params, expected_result: CheckResult
) -> None:
    assert (
        list(check_podman_containers(params, parse_podman_containers(string_table)))
        == expected_result
    )
