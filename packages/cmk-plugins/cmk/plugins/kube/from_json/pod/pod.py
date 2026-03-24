# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import TypedDict

from ...schemata import api
from ..metadata import _metadata_from_json, JSONObjectWithMetadata
from .container_status import pod_containers
from .pod_spec import JSONPodSpec, pod_spec
from .pod_status import JSONPodStatus, pod_status


class JSONPod(JSONObjectWithMetadata):
    spec: JSONPodSpec
    status: JSONPodStatus


class JSONPodList(TypedDict):
    items: Sequence[JSONPod]


def pod_from_client(pod: JSONPod, controllers: Sequence[api.Controller]) -> api.Pod:
    return api.Pod(
        uid=api.PodUID(pod["metadata"]["uid"]),
        metadata=_metadata_from_json(pod["metadata"]),
        status=pod_status(pod["status"]),
        spec=pod_spec(pod["spec"]),
        containers=pod_containers(pod["status"].get("containerStatuses")),
        init_containers=pod_containers(pod["status"].get("initContainerStatuses")),
        controllers=controllers,
    )
