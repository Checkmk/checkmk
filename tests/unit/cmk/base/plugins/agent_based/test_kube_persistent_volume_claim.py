#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import render, Result, State
from cmk.base.plugins.agent_based.kube_persistent_volume_claim import (
    _check_kube_pvc,
    VOLUME_DEFAULT_PARAMS,
)
from cmk.base.plugins.agent_based.utils.kube import (
    AttachedVolume,
    PersistentVolumeClaim,
    PersistentVolumeClaimPhase,
    PersistentVolumeClaimStatus,
    StorageRequirement,
)


class PVCStatusFactory(ModelFactory):
    __model__ = PersistentVolumeClaimStatus


class PVCFactory(ModelFactory):
    __model__ = PersistentVolumeClaim


class AttachedVolumeFactory(ModelFactory):
    __model__ = AttachedVolume


@pytest.fixture(name="bound_pvc")
def fixture_bounded_pvc() -> PersistentVolumeClaim:
    return PVCFactory.build(
        status=PVCStatusFactory.build(
            phase=PersistentVolumeClaimPhase.CLAIM_BOUND,
            capacity=StorageRequirement(storage=1000.0),
        )
    )


def test_pvc_with_no_volume(bound_pvc: PersistentVolumeClaim) -> None:
    result = _check_kube_pvc(
        bound_pvc.metadata.name,
        value_store={},
        pvc=bound_pvc,
        volume=None,
        params={},
        timestamp=60,
    )

    assert bound_pvc.status.capacity is not None
    assert [r.summary for r in result if isinstance(r, Result)] == [
        "Status: Bound",
        f"Capacity: {render.bytes(bound_pvc.status.capacity.storage)}",
    ]


def test_pvc_with_volume(bound_pvc: PersistentVolumeClaim) -> None:
    current_timestamp = 60
    volume = AttachedVolumeFactory.build(
        persistent_volume_claim=bound_pvc.metadata.name,
        free=1000,
        capacity=2000,
    )

    check_result = list(
        _check_kube_pvc(
            bound_pvc.metadata.name,
            value_store={f"{bound_pvc.metadata.name}.delta": (current_timestamp - 60, 0)},
            pvc=bound_pvc,
            volume=volume,
            params=VOLUME_DEFAULT_PARAMS,
            timestamp=current_timestamp,
        )
    )

    results = [r.summary for r in check_result if isinstance(r, Result)]
    expected_results = (
        "Status: Bound",
        "Used: 50.00% - 1000 B of 1.95 KiB",
        "trend per",
        "trend per",
        "Time left until disk full:",
    )

    assert all(summary.startswith(expected_results[i]) for i, summary in enumerate(results))


def test_pvc_with_critical_volume(bound_pvc: PersistentVolumeClaim) -> None:
    current_timestamp = 60
    volume = AttachedVolumeFactory.build(
        persistent_volume_claim=bound_pvc.metadata.name,
        free=100,
        capacity=2000,
    )

    check_result = _check_kube_pvc(
        bound_pvc.metadata.name,
        value_store={f"{bound_pvc.metadata.name}.delta": (current_timestamp - 60, 0)},
        pvc=bound_pvc,
        volume=volume,
        params=VOLUME_DEFAULT_PARAMS,
        timestamp=current_timestamp,
    )

    assert [r.state for r in check_result if isinstance(r, Result) and r.state == State.CRIT] == [
        State.CRIT
    ]
