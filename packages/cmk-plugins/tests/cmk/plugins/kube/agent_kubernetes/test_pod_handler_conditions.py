# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest

from cmk.plugins.kube.agent_handlers import pod_handler
from cmk.plugins.kube.schemata import api, section


# TODO: Remove for CMK 3.1
@pytest.mark.parametrize(
    "status, parsed_status",
    [
        (True, api.ConditionStatus.TRUE),
        (False, api.ConditionStatus.FALSE),
        ("True", api.ConditionStatus.TRUE),
        ("False", api.ConditionStatus.FALSE),
        ("Unknown", api.ConditionStatus.UNKNOWN),
    ],
)
def test_pod_condition_status_normalization(
    status: bool | str, parsed_status: api.ConditionStatus
) -> None:
    parsed = section.PodCondition.model_validate(
        {"status": status, "reason": "foo", "detail": "bar", "last_transition_time": 1337}
    )
    assert parsed.status == parsed_status
    assert parsed.reason == "foo"
    assert parsed.detail == "bar"
    assert parsed.last_transition_time == 1337


def test_pod_conditions_start_up() -> None:
    """
    It is possible that during startup of pods, also more complete
    information arises.
    """
    api_pod_status = api.PodStatus(
        start_time=api.convert_to_timestamp(
            datetime.datetime(2021, 11, 22, 16, 11, 38, 710257, tzinfo=datetime.UTC)
        ),
        conditions=[
            api.PodCondition(
                status=api.ConditionStatus.TRUE,
                type=api.ConditionType.INITIALIZED,
                custom_type=None,
                reason=None,
                detail=None,
            ),
            api.PodCondition(
                status=api.ConditionStatus.FALSE,
                type=api.ConditionType.READY,
                custom_type=None,
                reason="ContainersNotReady",
                detail="containers with unready status: [unready_container]",
            ),
            api.PodCondition(
                status=api.ConditionStatus.FALSE,
                type=api.ConditionType.CONTAINERSREADY,
                custom_type=None,
                reason="ContainersNotReady",
                detail="containers with unready status: [unready_container]",
            ),
            api.PodCondition(
                status=api.ConditionStatus.TRUE,
                type=api.ConditionType.PODSCHEDULED,
                custom_type=None,
                reason=None,
                detail=None,
            ),
        ],
        phase=api.Phase.PENDING,
        qos_class="burstable",
    )
    assert pod_handler._conditions(api_pod_status) == section.PodConditions(  # noqa: SLF001
        initialized=section.PodCondition(status=api.ConditionStatus.TRUE, reason=None, detail=None),
        scheduled=section.PodCondition(status=api.ConditionStatus.TRUE, reason=None, detail=None),
        containersready=section.PodCondition(
            status=api.ConditionStatus.FALSE,
            reason="ContainersNotReady",
            detail="containers with unready status: [unready_container]",
        ),
        ready=section.PodCondition(
            status=api.ConditionStatus.FALSE,
            reason="ContainersNotReady",
            detail="containers with unready status: [unready_container]",
        ),
    )


def test_pod_conditions_start_up_missing_fields() -> None:
    """
    In this specific instance all of the fields except for the scheduled
    field are missing.
    """
    api_pod_status = api.PodStatus(
        start_time=api.convert_to_timestamp(
            datetime.datetime(2021, 11, 22, 16, 11, 38, 710257, tzinfo=datetime.UTC)
        ),
        conditions=[
            api.PodCondition(
                status=api.ConditionStatus.TRUE,
                type=api.ConditionType.PODSCHEDULED,
                custom_type=None,
                reason=None,
                detail=None,
            )
        ],
        phase=api.Phase.PENDING,
        qos_class="burstable",
    )

    assert pod_handler._conditions(api_pod_status) == section.PodConditions(  # noqa: SLF001
        initialized=None,
        scheduled=section.PodCondition(status=api.ConditionStatus.TRUE, reason=None, detail=None),
        containersready=None,
        ready=None,
    )
