# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import cast, get_args, Literal, NotRequired, TypedDict, TypeGuard

from ...schemata import api
from .container_status import JSONContainerStatus
from .pod_condition import JSONPodCondition, pod_conditions


class JSONPodStatus(TypedDict):
    conditions: NotRequired[Sequence[JSONPodCondition]]
    phase: Literal["Running", "Pending", "Succeeded", "Failed", "Unknown"]
    startTime: NotRequired[str]
    hostIP: NotRequired[str]
    podIP: NotRequired[str]
    qosClass: NotRequired[str]
    initContainerStatuses: NotRequired[Sequence[JSONContainerStatus]]
    containerStatuses: NotRequired[Sequence[JSONContainerStatus]]


def pod_status(status: JSONPodStatus) -> api.PodStatus:
    def is_valid_qos_class(qos_class: str) -> TypeGuard[api.QosClass]:
        return qos_class in get_args(api.QosClass)

    raw_qos_class = status.get("qosClass")
    if raw_qos_class is not None:
        lower_qos_class = raw_qos_class.lower()
        if is_valid_qos_class(lower_qos_class):
            qos_class: api.QosClass | None = cast(api.QosClass, lower_qos_class)
        else:
            # This would be a great place to have some kind of "warn but don't crash" a la CMK-33032
            qos_class = None
    else:
        qos_class = None

    return api.PodStatus(
        conditions=pod_conditions(conditions) if (conditions := status.get("conditions")) else None,
        phase=api.Phase(status["phase"].lower()),
        start_time=api.convert_to_timestamp(start_time)
        if (start_time := status.get("startTime"))
        else None,
        host_ip=api.IpAddress(host_ip) if (host_ip := status.get("hostIP")) else None,
        pod_ip=api.IpAddress(pod_ip) if (pod_ip := status.get("podIP")) else None,
        qos_class=qos_class,
    )
