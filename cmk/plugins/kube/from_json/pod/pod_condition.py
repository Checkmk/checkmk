# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NotRequired, TypedDict

from ...schemata import api


class JSONPodCondition(TypedDict):
    status: str
    type: str
    reason: NotRequired[str]
    message: NotRequired[str]
    lastTransitionTime: NotRequired[str]


def pod_condition(condition: JSONPodCondition) -> api.PodCondition:
    type_ = api.ConditionType.from_kube_api(condition["type"])
    custom_type = None if type_ is not None else condition["type"]
    return api.PodCondition(
        # TODO: CMK-33030, the JSON type is right, the api model is wrong
        status=condition["status"],  # type: ignore[arg-type]
        reason=condition.get("reason"),
        detail=condition.get("message"),
        last_transition_time=(
            int(api.convert_to_timestamp(last_transition_time))
            if (last_transition_time := condition.get("lastTransitionTime"))
            else None
        ),
        type=type_,
        custom_type=custom_type,
    )


def pod_conditions(conditions: Sequence[JSONPodCondition]) -> list[api.PodCondition]:
    return [pod_condition(condition) for condition in conditions]
