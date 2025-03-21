#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.netapp.agent_based.netapp_ontap_snapshots import (
    check_netapp_ontap_snapshots,
    discover_netapp_ontap_snapshots,
)
from cmk.plugins.netapp.models import SvmModel, VolumeModel


class VolumeModelFactory(ModelFactory):
    __model__ = VolumeModel


class SvmModelFactory(ModelFactory):
    __model__ = SvmModel


_SVM_SECTION = {
    "svm1": SvmModelFactory.build(name="svm1", state=None, subtype="other"),
    "svm_metrocluster": SvmModelFactory.build(
        name="svm_metrocluster", state=None, subtype="sync_destination"
    ),
}


@pytest.mark.parametrize(
    "volume_model, expected_result",
    [
        pytest.param(
            VolumeModelFactory.build(
                name="volume1",
                state="offline",
                svm_name="svm1",
            ),
            [Service(item="svm1:volume1")],
            id="Snapshot discovered",
        ),
        pytest.param(
            VolumeModelFactory.build(
                name="volume1",
                state="offline",
                svm_name="svm_metrocluster",
            ),
            [],
            id="Snapshot not discovered",
        ),
    ],
)
def test_discover_netapp_ontap_snapshots(
    volume_model: VolumeModel, expected_result: DiscoveryResult
) -> None:
    snapshot_section = {volume_model.item_name(): volume_model}

    result = list(discover_netapp_ontap_snapshots(snapshot_section, _SVM_SECTION))

    assert result == expected_result


@pytest.mark.parametrize(
    "volume_model, params, expected_result",
    [
        pytest.param(
            VolumeModelFactory.build(
                name="volume1",
                state="offline",
                svm_name="svm1",
            ),
            {},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="No snapshot information available. Volume state is offline",
                )
            ],
            id="volume offline",
        ),
        pytest.param(
            VolumeModelFactory.build(
                name="volume1",
                state="online",
                svm_name="svm1",
                snapshot_used=None,
            ),
            {},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="No snapshot information available. Volume state is online",
                )
            ],
            id="volume without space information",
        ),
        pytest.param(
            VolumeModelFactory.build(
                name="volume1",
                state="online",
                svm_name="svm1",
                snapshot_used=5000,
                space_total=10000,
                snapshot_reserve_size=0,
            ),
            {},
            [
                Result(state=State.OK, summary="Used snapshot space: 4.88 KiB"),
                Metric("bytes", 5000.0),
                Result(state=State.WARN, summary="No snapshot reserve configured"),
            ],
            id="volume without snapshot reserve size warning",
        ),
        pytest.param(
            VolumeModelFactory.build(
                name="volume1",
                state="online",
                svm_name="svm1",
                snapshot_used=5000,
                space_total=10000,
                snapshot_reserve_size=0,
            ),
            {"state_noreserve": State.OK},
            [
                Result(state=State.OK, summary="Used snapshot space: 4.88 KiB"),
                Metric("bytes", 5000.0),
                Result(state=State.OK, summary="No snapshot reserve configured"),
            ],
            id="volume without snapshot reserve size status ok",
        ),
    ],
)
def test_check_netapp_ontap_snapshots_no_metrics(
    volume_model: VolumeModel, params: Mapping[str, Any], expected_result: CheckResult
) -> None:
    section = {volume_model.item_name(): volume_model}

    result = list(check_netapp_ontap_snapshots("svm1:volume1", params, section, _SVM_SECTION))

    assert result == expected_result


def test_check_netapp_ontap_snapshots_with_metrics() -> None:
    volume_model = VolumeModelFactory.build(
        name="volume1",
        state="online",
        svm_name="svm1",
        snapshot_used=2500,
        space_total=10000,
        snapshot_reserve_size=5000,
        snapshot_reserve_percent=50,
    )

    section = {volume_model.item_name(): volume_model}

    result = list(check_netapp_ontap_snapshots("svm1:volume1", {}, section, _SVM_SECTION))

    assert result == [
        Result(state=State.OK, summary="Reserve used: 50.0% (2.44 KiB)"),
        Result(state=State.OK, summary="Total Reserve: 50% (4.88 KiB) of 14.6 KiB"),
        Metric("bytes", 2500.0, boundaries=(0.0, 5000.0)),
    ]
