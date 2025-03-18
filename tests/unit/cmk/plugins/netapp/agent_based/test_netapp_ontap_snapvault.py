#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, State
from cmk.plugins.netapp.agent_based.netapp_ontap_snapvault import check_netapp_ontap_snapvault
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
    assert isinstance(result[1], Result)
    assert result[1].state == State.CRIT
