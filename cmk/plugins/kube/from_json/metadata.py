# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NotRequired, TypedDict

from ..schemata import api
from .owner_reference import JSONOwnerReferences


class JSONMetaData(TypedDict):
    uid: str
    name: str
    namespace: str
    creationTimestamp: NotRequired[str]
    labels: NotRequired[Mapping[str, str]]
    annotations: NotRequired[Mapping[str, str]]
    ownerReferences: NotRequired[JSONOwnerReferences]


class JSONObjectWithMetadata(TypedDict):
    metadata: JSONMetaData


def _metadata_from_json(metadata: JSONMetaData) -> api.MetaData:
    return api.MetaData.model_validate(metadata)


def dependent_object_uid_from_json(
    dependent: JSONObjectWithMetadata,
) -> str:
    return dependent["metadata"]["uid"]


def dependent_object_owner_references_from_json(
    dependent: JSONObjectWithMetadata,
) -> api.OwnerReferences:
    return [
        api.OwnerReference(
            uid=ref["uid"],
            controller=ref.get("controller"),
            kind=ref["kind"],
            name=ref["name"],
            namespace=dependent["metadata"].get("namespace"),
        )
        for ref in dependent["metadata"].get("ownerReferences", [])
    ]
