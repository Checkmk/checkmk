#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform_json import (
    dependent_object_owner_refererences_from_json,
    JSONStatefulSet,
    JSONStatefulSetOnDelete,
)

JSON_STATEFULSET: JSONStatefulSet = {
    "metadata": {
        "annotations": {},
        "creationTimestamp": "2022-07-18T09:16:52Z",
        "labels": {
            "controller-uid": "owner-reference-uid",
            "job-name": "owner-reference-name",
        },
        "name": "owner-reference-name-vmfg9",
        "namespace": "owner-reference-namespace",
        "ownerReferences": [
            {
                "controller": True,
                "kind": "Job",
                "name": "owner-reference-name",
                "uid": "owner-reference-uid",
            }
        ],
        "uid": "uid",
    },
    "spec": {
        "replicas": 2,
        "selector": {"matchLabels": {"controller-uid": "owner-reference-uid"}},
        "updateStrategy": JSONStatefulSetOnDelete(type="OnDelete"),
    },
    "status": {},
}

JSON_STATEFULSET_WITH_NO_OWNER_REFERENCES: JSONStatefulSet = {
    "metadata": {
        "annotations": {},
        "creationTimestamp": "2022-07-18T09:16:52Z",
        "labels": {
            "controller-uid": "owner-reference-uid",
            "job-name": "owner-reference-name",
        },
        "name": "owner-reference-name-vmfg9",
        "namespace": "owner-reference-namespace",
        "uid": "uid",
    },
    "spec": {
        "replicas": 2,
        "selector": {"matchLabels": {"controller-uid": "owner-reference-uid"}},
        "updateStrategy": JSONStatefulSetOnDelete(type="OnDelete"),
    },
    "status": {},
}


def test_dependent_object_owner_references_from_json() -> None:
    owner_reference = dependent_object_owner_refererences_from_json(JSON_STATEFULSET)[0]
    assert isinstance(owner_reference, api.OwnerReference)
    assert owner_reference.uid == "owner-reference-uid"
    assert owner_reference.controller is True
    assert owner_reference.kind == "Job"
    assert owner_reference.name == "owner-reference-name"
    assert owner_reference.namespace == "owner-reference-namespace"


def test_dependent_object_owner_references_from_json_with_no_owner_references_present() -> None:
    assert (
        dependent_object_owner_refererences_from_json(JSON_STATEFULSET_WITH_NO_OWNER_REFERENCES)
        == []
    )
