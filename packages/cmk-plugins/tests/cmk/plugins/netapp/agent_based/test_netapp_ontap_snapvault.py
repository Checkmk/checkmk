#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, State
from cmk.plugins.netapp.agent_based.netapp_ontap_snapvault import (
    check_netapp_ontap_snapvault,
    parse_netapp_ontap_snapmirror,
)
from cmk.plugins.netapp.models import SnapMirrorModel


class SnapMirrorModelFactory(ModelFactory):
    __model__ = SnapMirrorModel


def test_check_netapp_ontap_snapvault_data() -> None:
    snapmirror_model = SnapMirrorModelFactory.build(
        destination="snapmirror_destination",
        source_svm_name="svm_name",
        policy_name="policy_name",
        state=None,
        lag_time=None,
        transfer_state="transferring",
    )

    section = {snapmirror_model.destination: snapmirror_model}

    result = list(check_netapp_ontap_snapvault("snapmirror_destination", {}, section))

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
    )

    section = {snapmirror_model.destination: snapmirror_model}

    result = list(
        check_netapp_ontap_snapvault("snapmirror_destination", {"lag_time": (9000, 10000)}, section)
    )

    assert result[0] == Result(state=State.OK, summary="Destination-system: snapmirror_destination")
    assert isinstance(result[2], Result)
    assert result[2].state == State.CRIT


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
