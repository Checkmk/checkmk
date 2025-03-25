#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import render, Result, State
from cmk.plugins.collection.agent_based.kube_persistent_volume_claim import (
    _check_kube_pvc,
    VOLUME_DEFAULT_PARAMS,
)
from cmk.plugins.kube.schemata.api import PersistentVolumeClaimPhase
from cmk.plugins.kube.schemata.section import (
    AttachedVolume,
    PersistentVolume,
    PersistentVolumeClaim,
    PersistentVolumeClaimStatus,
    StorageRequirement,
)


class PVCStatusFactory(ModelFactory):
    __model__ = PersistentVolumeClaimStatus


class PVCFactory(ModelFactory):
    __model__ = PersistentVolumeClaim


class AttachedVolumeFactory(ModelFactory):
    __model__ = AttachedVolume


class PersistentVolumeFactory(ModelFactory):
    __model__ = PersistentVolume


@pytest.fixture(name="bound_pvc")
def fixture_bounded_pvc() -> PersistentVolumeClaim:
    return PVCFactory.build(
        status=PVCStatusFactory.build(
            phase=PersistentVolumeClaimPhase.CLAIM_BOUND,
            capacity=StorageRequirement(storage=1000),
        )
    )


def test_pvc_with_no_volume(bound_pvc: PersistentVolumeClaim) -> None:
    result = _check_kube_pvc(
        bound_pvc.metadata.name,
        value_store={},
        pvc=bound_pvc,
        persistent_volume=None,
        volume=None,
        params=VOLUME_DEFAULT_PARAMS,
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
            persistent_volume=None,
            params=VOLUME_DEFAULT_PARAMS,
            timestamp=current_timestamp,
        )
    )

    results = [r.summary for r in check_result if isinstance(r, Result)]
    assert results[0].startswith("Status: Bound")
    assert results[1].startswith("Used: 50.00% - 1000 B of 1.95 KiB")
    assert results[2].startswith("trend per")
    assert results[3].startswith("trend per")
    assert results[4].startswith("Time left until disk full:")


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
        persistent_volume=None,
        params=VOLUME_DEFAULT_PARAMS,
        timestamp=current_timestamp,
    )

    assert [r.state for r in check_result if isinstance(r, Result) and r.state == State.CRIT] == [
        State.CRIT
    ]


def test_pvc_with_persistent_volume(bound_pvc: PersistentVolumeClaim) -> None:
    """Test the details content when PV is available."""
    persistent_volume = PersistentVolumeFactory.build()
    check_result = _check_kube_pvc(
        bound_pvc.metadata.name,
        value_store={},
        pvc=bound_pvc,
        volume=None,
        persistent_volume=persistent_volume,
        params=VOLUME_DEFAULT_PARAMS,
        timestamp=60,
    )

    details = " ".join(r.details for r in check_result if isinstance(r, Result))
    assert "Status" in details
    assert "StorageClass" in details
    assert "Access Modes" in details
    assert "VolumeMode" in details
    assert "Mounted Volume" in details


def test_pvc_first_time_pending_status():
    """Test that the value store is updated when PVC with pending status is seen for first time."""
    pending_pvc = PVCFactory.build(
        status=PVCStatusFactory.build(
            phase=PersistentVolumeClaimPhase.CLAIM_PENDING,
            capacity=StorageRequirement(storage=1000),
        )
    )
    value_store: dict[str, Any] = {}
    timestamp = 300
    _ = list(
        _check_kube_pvc(
            pending_pvc.metadata.name,
            value_store=value_store,
            pvc=pending_pvc,
            volume=None,
            persistent_volume=None,
            params={**VOLUME_DEFAULT_PARAMS, "pending": ("levels", (300, 600))},
            timestamp=timestamp,
        )
    )
    assert value_store == {"pending": timestamp}


def test_pvc_warn_pending_status():
    """Test that PVC with pending status is in warning state due to matching WARN threshold."""
    pending_pvc = PVCFactory.build(
        status=PVCStatusFactory.build(
            phase=PersistentVolumeClaimPhase.CLAIM_PENDING,
            capacity=StorageRequirement(storage=1000),
        )
    )
    check_result = list(
        _check_kube_pvc(
            pending_pvc.metadata.name,
            value_store={"pending": 0},
            pvc=pending_pvc,
            volume=None,
            persistent_volume=None,
            params={**VOLUME_DEFAULT_PARAMS, "pending": ("levels", (300, 600))},
            timestamp=300,
        )
    )
    assert [
        r.state for r in check_result if isinstance(r, Result) and r.summary.startswith("Status")
    ] == [State.WARN]


def test_pvc_lost_status_as_ok_state():
    """Test that PVC with lost phase status is reported as OK due params."""
    lost_pvc = PVCFactory.build(
        status=PVCStatusFactory.build(
            phase=PersistentVolumeClaimPhase.CLAIM_LOST,
            capacity=StorageRequirement(storage=1000),
        )
    )
    check_result = list(
        _check_kube_pvc(
            lost_pvc.metadata.name,
            value_store={},
            pvc=lost_pvc,
            volume=None,
            persistent_volume=None,
            params={**VOLUME_DEFAULT_PARAMS, "lost": 0},
            timestamp=0,
        )
    )
    assert [
        r.state for r in check_result if isinstance(r, Result) and r.summary.startswith("Status")
    ] == [State.OK]
