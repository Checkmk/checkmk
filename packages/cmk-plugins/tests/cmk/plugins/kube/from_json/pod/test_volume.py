# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.kube.from_json.pod.volume import parse_pod_volume, parse_pod_volumes
from cmk.plugins.kube.schemata.api import VolumeName


def test_volume_with_pvc() -> None:
    result = parse_pod_volume(
        {
            "name": "data-vol",
            "persistentVolumeClaim": {"claimName": "my-claim", "readOnly": True},
        }
    )
    assert result.name == VolumeName("data-vol")
    assert result.persistent_volume_claim is not None
    assert result.persistent_volume_claim.claim_name == "my-claim"
    assert result.persistent_volume_claim.read_only is True


def test_volume_with_pvc_no_readonly() -> None:
    result = parse_pod_volume(
        {
            "name": "data-vol",
            "persistentVolumeClaim": {"claimName": "my-claim"},
        }
    )
    assert result.persistent_volume_claim is not None
    assert result.persistent_volume_claim.read_only is None


def test_volume_without_pvc() -> None:
    result = parse_pod_volume({"name": "tmp"})
    assert result.name == VolumeName("tmp")
    assert result.persistent_volume_claim is None


def test_parse_pod_volumes_mixed() -> None:
    results = parse_pod_volumes(
        [
            {"name": "pvc-vol", "persistentVolumeClaim": {"claimName": "claim-1"}},
            {"name": "emptydir-vol"},
        ]
    )
    assert len(results) == 2
    assert results[0].persistent_volume_claim is not None
    assert results[1].persistent_volume_claim is None
