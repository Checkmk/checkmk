#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import datetime
from collections.abc import Mapping

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.netapp.agent_based.netapp_ontap_snapvault import (
    check_netapp_ontap_snapvault,
    check_plugin_netapp_ontap_snapmirror,
    discover_netapp_ontap_snapvault,
    parse_netapp_ontap_snapmirror,
)
from cmk.plugins.netapp.models import SnapMirrorModel


class SnapMirrorModelFactory(ModelFactory):
    __model__ = SnapMirrorModel


DEFAULT_PARAMS = check_plugin_netapp_ontap_snapmirror.check_default_parameters or {}


def test_check_netapp_ontap_snapvault_data() -> None:
    snapmirror_model = SnapMirrorModelFactory.build(
        destination="snapmirror_destination",
        source_svm_name="svm_name",
        policy_name="policy_name",
        state=None,
        lag_time=None,
        transfer_state="transferring",
        healthy=None,
    )

    section = {snapmirror_model.destination: snapmirror_model}

    result = list(check_netapp_ontap_snapvault("snapmirror_destination", DEFAULT_PARAMS, section))

    assert result == [
        Result(state=State.OK, summary="Source-system: svm_name"),
        Result(state=State.OK, summary="Destination-system: snapmirror_destination"),
        Result(state=State.OK, summary="Policy: policy_name"),
        Result(state=State.OK, summary="Transfer State: transferring"),
    ]


def test_check_netapp_ontap_snapvault_metrics_ok() -> None:
    snapmirror_model = SnapMirrorModelFactory.build(
        destination="snapmirror_destination",
        source_svm_name=None,
        policy_name=None,
        state=None,
        lag_time="P1D",  # 86400 seconds
        transfer_state=None,
        healthy=None,
    )

    section = {snapmirror_model.destination: snapmirror_model}

    result = list(
        check_netapp_ontap_snapvault(
            "snapmirror_destination", {"lag_time": (90000, 100000)}, section
        )
    )

    assert result == [
        Result(state=State.OK, summary="Destination-system: snapmirror_destination"),
        Result(state=State.OK, summary="Policy not set"),
        Result(state=State.OK, summary="Lag time: 1 day 0 hours"),
    ]


def test_check_netapp_ontap_snapvault_metrics_crit() -> None:
    snapmirror_model = SnapMirrorModelFactory.build(
        destination="snapmirror_destination",
        source_svm_name=None,
        policy_name=None,
        state=None,
        lag_time="P1D",  # 86400 seconds
        transfer_state=None,
        healthy=None,
    )

    section = {snapmirror_model.destination: snapmirror_model}

    result = list(
        check_netapp_ontap_snapvault("snapmirror_destination", {"lag_time": (9000, 10000)}, section)
    )

    assert result[0] == Result(state=State.OK, summary="Destination-system: snapmirror_destination")
    assert isinstance(result[2], Result)
    assert result[2].state == State.CRIT


@pytest.mark.parametrize(
    ["policy_name", "expected_state"],
    [
        pytest.param("Asynchronous", State.CRIT, id="policy levels win"),
        pytest.param("Other", State.OK, id="default levels for other policies"),
    ],
)
def test_check_policy_lag_time(policy_name: str, expected_state: State) -> None:
    snapmirror_model = SnapMirrorModelFactory.build(
        destination="snapmirror_destination",
        source_svm_name=None,
        policy_name=policy_name,
        state=None,
        lag_time="P1D",  # 86400 seconds
        transfer_state=None,
        healthy=None,
    )
    params = {
        "lag_time": (90000.0, 100000.0),
        "policy_lag_time": [("Asynchronous", (9000.0, 10000.0))],
    }

    result = list(
        check_netapp_ontap_snapvault(
            "snapmirror_destination", params, {snapmirror_model.destination: snapmirror_model}
        )
    )

    assert isinstance(result[-1], Result)
    assert result[-1].state == expected_state


@pytest.mark.parametrize(
    ["transfer_state", "expected_state"],
    [
        pytest.param("success", State.OK, id="success"),
        pytest.param("transferring", State.OK, id="transferring"),
        pytest.param("queued", State.OK, id="queued"),
        pytest.param("aborted", State.CRIT, id="aborted"),
        pytest.param("hard_aborted", State.CRIT, id="hard_aborted"),
        pytest.param("failed", State.CRIT, id="failed"),
        pytest.param("new_ontap_state", State.UNKNOWN, id="unknown state"),
    ],
)
def test_check_transfer_state_with_plugin_defaults(
    transfer_state: str, expected_state: State
) -> None:
    model = SnapMirrorModelFactory.build(
        destination="snapmirror_destination",
        source_svm_name=None,
        policy_name=None,
        state=None,
        lag_time=None,
        transfer_state=transfer_state,
        healthy=None,
    )

    result = list(
        check_netapp_ontap_snapvault(
            "snapmirror_destination", DEFAULT_PARAMS, {model.destination: model}
        )
    )

    assert Result(state=expected_state, summary=f"Transfer State: {transfer_state}") in result


def test_check_transfer_state_is_configurable() -> None:
    model = SnapMirrorModelFactory.build(
        destination="snapmirror_destination",
        source_svm_name=None,
        policy_name=None,
        state=None,
        lag_time=None,
        transfer_state="failed",
        healthy=None,
    )
    params = {
        "transfer_state": {
            "aborted": 2,
            "failed": 1,
            "hard_aborted": 2,
            "queued": 0,
            "success": 0,
            "transferring": 0,
        }
    }

    result = list(
        check_netapp_ontap_snapvault("snapmirror_destination", params, {model.destination: model})
    )

    assert Result(state=State.WARN, summary="Transfer State: failed") in result


def test_parse_snapmirror_unknown_transfer_state() -> None:
    model = SnapMirrorModel(destination="svm:vol_dest", transfer_state="new_ontap_state")
    section = parse_netapp_ontap_snapmirror([[model.model_dump_json()]])
    assert section["svm:vol_dest"].transfer_state == "new_ontap_state"


def test_parse_snapmirror_cloud_destination_no_svm() -> None:
    # MetroCluster cloud/object-store destinations have no destination SVM (SUP-28199).
    # Verify such models round-trip through the parse function correctly.
    destination_path = "netapp-dj77748-0a9a-11ee-872f-dkii88e-mc:/objstore/not_vvvm-05_v005_0_dst"
    model = SnapMirrorModel(
        destination=destination_path,
        source_svm_name="308177c1-3c44-11ee-901f-dkii88e",
        policy_name="CloudBackupService-vzug_not_vvvm-05_cbs_mc",
        policy_type="async",
        transfer_state="success",
    )
    section = parse_netapp_ontap_snapmirror([[model.model_dump_json()]])
    assert destination_path in section
    assert section[destination_path].source_svm_name == "308177c1-3c44-11ee-901f-dkii88e"


def test_discover_relationships_without_lag_time() -> None:
    section = {
        "svm:vol_ok": SnapMirrorModel(
            destination="svm:vol_ok", lag_time=datetime.timedelta(hours=1)
        ),
        "svm:vol_never_transferred": SnapMirrorModel(
            destination="svm:vol_never_transferred", transfer_state="failed"
        ),
    }

    services = list(
        discover_netapp_ontap_snapvault({"exclude_destination_vserver": False}, section)
    )

    assert services == [Service(item="svm:vol_ok"), Service(item="svm:vol_never_transferred")]


@pytest.mark.parametrize(
    ["params", "expected_state"],
    [
        pytest.param(DEFAULT_PARAMS, State.CRIT, id="default"),
        pytest.param({**DEFAULT_PARAMS, "unhealthy_state": 1}, State.WARN, id="configured"),
    ],
)
def test_check_unhealthy_relationship(params: Mapping[str, object], expected_state: State) -> None:
    model = SnapMirrorModel(
        destination="svm:vol",
        healthy=False,
        unhealthy_reason=["Transfer failed.", "Destination volume is offline."],
    )

    result = list(check_netapp_ontap_snapvault("svm:vol", params, {model.destination: model}))

    assert (
        Result(
            state=expected_state,
            summary="Unhealthy: Transfer failed., Destination volume is offline.",
        )
        in result
    )


@pytest.mark.parametrize(
    ["healthy", "health_results"],
    [
        pytest.param(True, [Result(state=State.OK, notice="Healthy")], id="healthy"),
        pytest.param(None, [], id="not reported by ONTAP"),
    ],
)
def test_check_health_without_alert(healthy: bool | None, health_results: list[Result]) -> None:
    model = SnapMirrorModel(destination="svm:vol", healthy=healthy)

    result = list(
        check_netapp_ontap_snapvault("svm:vol", DEFAULT_PARAMS, {model.destination: model})
    )

    assert result == [
        Result(state=State.OK, summary="Destination-system: svm:vol"),
        Result(state=State.OK, summary="Policy not set"),
        *health_results,
    ]
