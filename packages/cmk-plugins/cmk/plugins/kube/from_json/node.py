# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import NotRequired, TypedDict

from ..schemata import api


# Let's unify this with JSONObjectWithMetadata at some point.
# The annoyance is that nodes don't have a namespace and we have to know if
# we have a namespace or not to know how to parse into schemata.api later.
class JSONNodeMetaData(TypedDict):
    name: api.NodeName
    creationTimestamp: str
    labels: NotRequired[Mapping[str, str]]
    annotations: NotRequired[Mapping[str, str]]


class JSONNode(TypedDict):
    metadata: JSONNodeMetaData
    status: object


class JSONNodeList(TypedDict):
    items: Sequence[JSONNode]


def _metadata_no_namespace_from_json(metadata: JSONNodeMetaData) -> api.NodeMetaData:
    return api.NodeMetaData.model_validate(metadata)


def node_list_from_json(
    node_list_raw: JSONNodeList,
    node_to_kubelet_health: Mapping[str, api.HealthZ | api.NodeConnectionError],
) -> Sequence[api.Node]:
    return [
        api.Node(
            metadata=_metadata_no_namespace_from_json(node["metadata"]),
            status=api.NodeStatus.model_validate(node["status"]),
            kubelet_health=node_to_kubelet_health[node["metadata"]["name"]],
        )
        for node in node_list_raw["items"]
    ]
