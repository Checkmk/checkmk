# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.kube.from_json.metadata import _metadata_from_json
from cmk.plugins.kube.schemata.api import Label, LabelName, LabelValue


def test_metadata_with_all_fields() -> None:
    metadata = _metadata_from_json(
        {
            "uid": "abc-123",
            "name": "my-pod",
            "namespace": "default",
            "creationTimestamp": "2022-03-28T09:19:41Z",
            "labels": {"app": "web"},
            "annotations": {"foo": "bar"},
        }
    )
    assert metadata.name == "my-pod"
    assert metadata.namespace == "default"
    assert metadata.creation_timestamp is not None
    assert metadata.labels == {
        LabelName("app"): Label(name=LabelName("app"), value=LabelValue("web"))
    }
    assert metadata.annotations == {"foo": "bar"}


def test_metadata_missing_labels_and_annotations() -> None:
    metadata = _metadata_from_json(
        {
            "uid": "abc-123",
            "name": "my-pod",
            "namespace": "default",
            "creationTimestamp": "2022-03-28T09:19:41Z",
        }
    )
    assert metadata.labels == {}
    assert metadata.annotations == {}


def test_metadata_missing_creation_timestamp() -> None:
    metadata = _metadata_from_json(
        {
            "uid": "abc-123",
            "name": "my-pod",
            "namespace": "default",
        }
    )
    assert metadata.creation_timestamp is None
