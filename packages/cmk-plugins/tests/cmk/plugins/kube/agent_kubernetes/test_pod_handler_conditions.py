# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from unittest import TestCase

from cmk.plugins.kube.agent_handlers import pod_handler
from cmk.plugins.kube.schemata import api, section


class TestPodStartUp(TestCase):
    """
    During startup of a large number of pods, special pod conditions may arise,
    where most of the information is missing. Depending on timing, we obtain
    different client objects from the kubernetes api.
    """

    def test_pod_conditions_start_up(self) -> None:
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
                    status=True,
                    type=api.ConditionType.INITIALIZED,
                    custom_type=None,
                    reason=None,
                    detail=None,
                ),
                api.PodCondition(
                    status=False,
                    type=api.ConditionType.READY,
                    custom_type=None,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
                api.PodCondition(
                    status=False,
                    type=api.ConditionType.CONTAINERSREADY,
                    custom_type=None,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
                api.PodCondition(
                    status=True,
                    type=api.ConditionType.PODSCHEDULED,
                    custom_type=None,
                    reason=None,
                    detail=None,
                ),
            ],
            phase=api.Phase.PENDING,
            qos_class="burstable",
        )
        self.assertEqual(
            pod_handler._conditions(api_pod_status),  # noqa: SLF001
            section.PodConditions(
                initialized=section.PodCondition(status=True, reason=None, detail=None),
                scheduled=section.PodCondition(status=True, reason=None, detail=None),
                containersready=section.PodCondition(
                    status=False,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
                ready=section.PodCondition(
                    status=False,
                    reason="ContainersNotReady",
                    detail="containers with unready status: [unready_container]",
                ),
            ),
        )

    def test_pod_conditions_start_up_missing_fields(self) -> None:
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
                    status=True,
                    type=api.ConditionType.PODSCHEDULED,
                    custom_type=None,
                    reason=None,
                    detail=None,
                )
            ],
            phase=api.Phase.PENDING,
            qos_class="burstable",
        )

        self.assertEqual(
            pod_handler._conditions(api_pod_status),  # noqa: SLF001
            section.PodConditions(
                initialized=None,
                scheduled=section.PodCondition(status=True, reason=None, detail=None),
                containersready=None,
                ready=None,
            ),
        )
