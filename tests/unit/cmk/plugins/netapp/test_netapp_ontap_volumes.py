#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.lib.df import (
    FILESYSTEM_DEFAULT_LEVELS,
    INODES_DEFAULT_PARAMS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
    TREND_DEFAULT_PARAMS,
)
from cmk.plugins.netapp.agent_based.netapp_ontap_volumes import (
    _generate_volume_metrics,
    _serialize_volumes,
    check_volumes,
    discover_netapp_ontap_volumes,
    VolumesCountersSection,
)
from cmk.plugins.netapp.models import SvmModel, VolumeCountersModel, VolumeModel


class VolumeModelFactory(ModelFactory):
    __model__ = VolumeModel


class VolumeCountersModelFactory(ModelFactory):
    __model__ = VolumeCountersModel


class SvmModelFactory(ModelFactory):
    __model__ = SvmModel


LAST_EVALUATION_SECONDS = 0
NOW_SIMULATED_SECONDS = 2000

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


_COUNTER = VolumeCountersModelFactory.build(
    id="volume_counter_1",
    total_read_ops=1000,
    bytes_written=1000,
    bytes_read=1000,
    total_write_ops=1000,
    fcp_read_ops=1000,
    fcp_read_data=1000,
)

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
            id="Volume discovered",
        ),
        pytest.param(
            VolumeModelFactory.build(
                name="volume1",
                state="offline",
                svm_name="svm_metrocluster",
            ),
            [],
            id="Volume not discovered",
        ),
    ],
)
def test_discover_netapp_ontap_volumes(
    volume_model: VolumeModel, expected_result: DiscoveryResult
) -> None:
    volumes_section = {volume_model.item_name(): volume_model}

    result = list(discover_netapp_ontap_volumes([], volumes_section, None, _SVM_SECTION))

    assert result == expected_result


def test_generate_volume_metrics_no_data_to_monitor() -> None:
    result = list(_generate_volume_metrics({}, {"perfdata": []}, _COUNTER, NOW_SIMULATED_SECONDS))

    assert len(result) == 0


def test_generate_volume_metrics_empty_protocol() -> None:
    value_store = {
        #                 last time, last value
        "total_read_ops": (LAST_EVALUATION_SECONDS, 0),
        "bytes_written": (LAST_EVALUATION_SECONDS, 0),
        "bytes_read": (LAST_EVALUATION_SECONDS, 0),
        "total_write_ops": (LAST_EVALUATION_SECONDS, 0),
    }

    result = list(
        _generate_volume_metrics(value_store, {"perfdata": [""]}, _COUNTER, NOW_SIMULATED_SECONDS)
    )

    assert result == [
        Metric("total_read_ops", 0.5),
        Metric("bytes_written", 0.5),
        Metric("bytes_read", 0.5),
        Metric("total_write_ops", 0.5),
    ]


def test_generate_volume_metrics() -> None:
    value_store = {
        #                 last time, last value
        "fcp_read_ops": (LAST_EVALUATION_SECONDS, 0),
        "fcp_read_data": (LAST_EVALUATION_SECONDS, 0),
    }

    result = list(
        _generate_volume_metrics(
            value_store, {"perfdata": ["fcp"]}, _COUNTER, NOW_SIMULATED_SECONDS
        )
    )

    assert result == [
        Metric("fcp_read_data", 0.5),
        Metric("fcp_read_ops", 0.5),
    ]


def test_serialize_volumes() -> None:
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
        ),
    ]

    volumes_section = {vol_obj.item_name(): vol_obj for vol_obj in volume_models}
    volumes_counters_section = {
        counter_obj.item_name(): counter_obj for counter_obj in _VOLUME_COUNTERS_MODELS
    }

    result = _serialize_volumes(volumes_section, volumes_counters_section)

    assert "svm_name:volume_name" in result
    assert result["svm_name:volume_name"]["fcp_read_latency"] == 1000
    assert result["svm_name:volume_name"]["space_available"] == 500
    assert result["svm_name:volume_name"]["id"] == "node_name:svm_name:volume_name:volume_uuid"


def test_serialize_volumes_no_counters() -> None:
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
        ),
    ]

    volumes_section = {vol_obj.item_name(): vol_obj for vol_obj in volume_models}
    volumes_counters_section: VolumesCountersSection = {}

    result = _serialize_volumes(volumes_section, volumes_counters_section)

    assert "svm_name:volume_name" in result
    assert "id" not in result["svm_name:volume_name"]
    assert result["svm_name:volume_name"]["state"] == "OK"
    assert result["svm_name:volume_name"]["space_available"] == 500


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

    result = list(
        check_volumes(
            "svm_name:volume_name",
            {},
            volumes_section,
            volumes_counters_section,
            {},
            NOW_SIMULATED_SECONDS,
        )
    )

    assert result == [Result(state=State.WARN, summary="Volume state OK")]


_VOLUME_MODELS = [
    # with counters
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
    ),
    # without counters
    VolumeModelFactory.build(
        uuid="volume_uuid1",
        state="online",
        name="volume_name1",
        msid=100,
        svm_name="svm_name",
        svm_uuid="svm_uuid",
        space_available=500,
        space_total=1000,
        logical_used=500,
        files_maximum=1000,
        files_used=500,
        logical_enforcement=False,
    ),
]


@pytest.mark.parametrize(
    "volume_id, expected_result_qty",
    [
        pytest.param(
            "svm_name:volume_name",
            15,
            id="volume with counters",
        ),
        pytest.param(
            "svm_name:volume_name1",
            13,
            id="volume without counters",
        ),
    ],
)
def test_check_netapp_ontap_volumes_state_online(volume_id: str, expected_result_qty: int) -> None:
    volumes_section = {vol_obj.item_name(): vol_obj for vol_obj in _VOLUME_MODELS}
    volumes_counters_section = {
        counter_obj.item_name(): counter_obj for counter_obj in _VOLUME_COUNTERS_MODELS
    }

    default_params = {
        **FILESYSTEM_DEFAULT_LEVELS,
        **MAGIC_FACTOR_DEFAULT_PARAMS,
        **INODES_DEFAULT_PARAMS,
        **TREND_DEFAULT_PARAMS,
    }
    # also test counters
    default_params = default_params | {
        "perfdata": [""],
    }

    value_store = {
        #                 last time, last value
        "svm_name:volume_name.delta": (LAST_EVALUATION_SECONDS, 0),
        "svm_name:volume_name1.delta": (LAST_EVALUATION_SECONDS, 0),
        "bytes_written": (LAST_EVALUATION_SECONDS, 0),
        "bytes_read": (LAST_EVALUATION_SECONDS, 0),
    }

    result = list(
        check_volumes(
            volume_id,
            default_params,
            volumes_section,
            volumes_counters_section,
            value_store,
            NOW_SIMULATED_SECONDS,
        )
    )

    assert len(result) == expected_result_qty
    assert isinstance(result[0], Metric)
    assert result[0].name == "fs_used"
    assert isinstance(result[1], Metric)
    assert result[1].name == "fs_free"
