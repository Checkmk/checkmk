#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from polyfactory.factories.pydantic_factory import ModelFactory

import cmk.plugins.netapp.agent_based.netapp_ontap_volumes as ontap_vol
from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib.df import (
    FILESYSTEM_DEFAULT_LEVELS,
    INODES_DEFAULT_PARAMS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
    TREND_DEFAULT_PARAMS,
)
from cmk.plugins.netapp.agent_based.netapp_ontap_volumes import (
    _generate_volume_metrics,
    _serialize_volumes,
    check_netapp_ontap_volumes,
)
from cmk.plugins.netapp.models import VolumeCountersModel, VolumeModel


class VolumeModelFactory(ModelFactory):
    __model__ = VolumeModel


class VolumeCountersModelFactory(ModelFactory):
    __model__ = VolumeCountersModel


NOW_SIMULATED_SECONDS = 0
LAST_EVALUATION_SECONDS = -2000

_VOLUME_COUNTERS_MODELS = [
    VolumeCountersModelFactory.build(
        id="node_name:svm_name:volume_name:volume_uuid",
        fcp_write_data=1000,
        fcp_read_latency=1000,
        iscsi_write_latency=1000,
        read_latency=1000,
        nfs_write_ops=1000,
    ),
]

_VOLUMES_MODELS = [
    VolumeModelFactory.build(
        uuid="volume_uuid",
        state="OK",
        name="volume_name",
        msid=100,
        svm_name="svm_name",
        svm_uuid="svm_uuid",
        space_available=500,
        space_total=1000,
        logical_used=500,
        files_maximum=1000,
        files_used=500,
    ),
]


_VALUE_STORE = {
    #                 last time, last value
    "total_read_ops": (LAST_EVALUATION_SECONDS, 0),
    "bytes_written": (LAST_EVALUATION_SECONDS, 0),
    "bytes_read": (LAST_EVALUATION_SECONDS, 0),
    "total_write_ops": (LAST_EVALUATION_SECONDS, 0),
    "fcp_read_ops": (LAST_EVALUATION_SECONDS, 0),
    "fcp_read_data": (LAST_EVALUATION_SECONDS, 0),
    "svm_name:volume_name.delta": (LAST_EVALUATION_SECONDS, 0),
}

_COUNTER = VolumeCountersModelFactory.build(
    id="volume_counter_1",
    total_read_ops=1000,
    bytes_written=1000,
    bytes_read=1000,
    total_write_ops=1000,
    fcp_read_ops=1000,
    fcp_read_data=1000,
)


def test_generate_volume_metrics_no_data_to_monitor() -> None:
    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(_generate_volume_metrics(_VALUE_STORE, {"perfdata": []}, _COUNTER))

        assert len(result) == 0


def test_generate_volume_metrics_empty_protocol() -> None:
    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(_generate_volume_metrics(_VALUE_STORE, {"perfdata": [""]}, _COUNTER))

        assert result == [
            Metric("total_read_ops", 0.5),
            Metric("bytes_written", 0.5),
            Metric("bytes_read", 0.5),
            Metric("total_write_ops", 0.5),
        ]


def test_generate_volume_metrics() -> None:
    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(_generate_volume_metrics(_VALUE_STORE, {"perfdata": ["fcp"]}, _COUNTER))

        assert result == [
            Metric("fcp_read_data", 0.5),
            Metric("fcp_read_ops", 0.5),
        ]


def test_serialize_volumes() -> None:
    volumes_section = {vol_obj.item_name(): vol_obj for vol_obj in _VOLUMES_MODELS}
    volumes_counters_section = {
        counter_obj.item_name(): counter_obj for counter_obj in _VOLUME_COUNTERS_MODELS
    }

    result = _serialize_volumes(volumes_section, volumes_counters_section)

    assert "svm_name:volume_name" in result
    assert result["svm_name:volume_name"]["fcp_read_latency"] == 1000
    assert result["svm_name:volume_name"]["space_available"] == 500
    assert result["svm_name:volume_name"]["id"] == "node_name:svm_name:volume_name:volume_uuid"


def test_check_netapp_ontap_volumes_state_not_online() -> None:
    volume_models = [
        VolumeModelFactory.build(
            uuid="volume_uuid",
            state="OK",
            name="volume_name",
            msid=100,
            svm_name="svm_name",
            svm_uuid="svm_uuid",
            space_available=500,
            space_total=1000,
            logical_used=500,
            files_maximum=1000,
            files_used=500,
        )
    ]

    volumes_section = {vol_obj.item_name(): vol_obj for vol_obj in volume_models}
    volumes_counters_section = {
        counter_obj.item_name(): counter_obj for counter_obj in _VOLUME_COUNTERS_MODELS
    }

    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(
            check_netapp_ontap_volumes(
                "svm_name:volume_name", {}, volumes_section, volumes_counters_section
            )
        )

        assert result == [Result(state=State.WARN, summary="Volume state OK")]


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    # According to NetApp's "Performance Management Design Guide",
    # the latency is a function of `total_ops`.
    monkeypatch.setattr(ontap_vol, "get_value_store", lambda: _VALUE_STORE)


def test_check_netapp_ontap_volumes_state_online(value_store_patch: None) -> None:
    volume_models = [
        VolumeModelFactory.build(
            uuid="volume_uuid",
            state="online",
            name="volume_name",
            msid=100,
            svm_name="svm_name",
            svm_uuid="svm_uuid",
            space_available=500,
            space_total=1000,
            logical_used=500,
            files_maximum=1000,
            files_used=500,
            logical_enforcement=False,
        )
    ]

    volumes_section = {vol_obj.item_name(): vol_obj for vol_obj in volume_models}
    volumes_counters_section = {
        counter_obj.item_name(): counter_obj for counter_obj in _VOLUME_COUNTERS_MODELS
    }

    default_params = {
        **FILESYSTEM_DEFAULT_LEVELS,
        **MAGIC_FACTOR_DEFAULT_PARAMS,
        **INODES_DEFAULT_PARAMS,
        **TREND_DEFAULT_PARAMS,
    }

    with time_machine.travel(datetime.fromtimestamp(NOW_SIMULATED_SECONDS, tz=ZoneInfo("UTC"))):
        result = list(
            check_netapp_ontap_volumes(
                "svm_name:volume_name", default_params, volumes_section, volumes_counters_section
            )
        )

        assert len(result) == 14
        assert isinstance(result[0], Metric)
        assert result[0].name == "fs_used"
        assert isinstance(result[1], Metric)
        assert result[1].name == "fs_free"

        assert isinstance(result[-1], Metric)
        assert result[-1].name == "space_savings"
        assert result[-1].value == 0.0
