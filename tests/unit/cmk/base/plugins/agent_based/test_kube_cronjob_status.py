#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Union

from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based import kube_cronjob_status
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.utils import kube
from cmk.base.plugins.agent_based.utils.kube import (
    ContainerRunningState,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    Timestamp,
)


class JobPodFactory(ModelFactory):
    __model__ = kube.JobPod


class JobConditionFactory(ModelFactory):
    __model__ = kube.JobCondition


class JobStatusFactory(ModelFactory):
    __model__ = kube.JobStatus

    conditions = [
        kube.JobCondition(type_=kube.JobConditionType.COMPLETE, status=kube.ConditionStatus.TRUE)
    ]
    start_time = Timestamp(1.0)


class CronJobLatestJobFactory(ModelFactory):
    __model__ = kube.CronJobLatestJob

    status = JobStatusFactory.build()
    pods = JobPodFactory.batch(size=1)


class CronJobStatusFactory(ModelFactory):
    __model__ = kube.CronJobStatus

    last_successful_time = Timestamp(1.0)
    last_schedule_time = Timestamp(1.0)


def _mocked_container_info_from_state(  # type:ignore[no-untyped-def]
    state: Union[ContainerRunningState, ContainerTerminatedState, ContainerWaitingState]
):
    # The check only requires the state field to be populated, therefore all the other fields are
    # filled with some arbitrary values.
    return ContainerStatus(
        container_id="some_id",
        image_id="some_other_id",
        name="some_name",
        image="some_image",
        ready=False,
        state=state,
        restart_count=0,
    )


def test_cron_job_status_time_outputs() -> None:
    """Test that checks time related outputs"""
    latest_job = CronJobLatestJobFactory.build()
    cron_job_status = CronJobStatusFactory.build(
        last_succesful_time=Timestamp(1.0),
        last_schedule_time=Timestamp(1.0),
    )

    check_result = list(
        kube_cronjob_status._check_cron_job_status(Timestamp(2.0), {}, cron_job_status, latest_job)
    )

    assert {r.summary for r in check_result if isinstance(r, Result)}.issuperset(
        {"Time since last successful completion: 1 second", "Time since last schedule: 1 second"}
    )
    assert {r.name for r in check_result if isinstance(r, Metric)}.issuperset(
        {
            "kube_cron_job_status_since_completion",
            "kube_cron_job_status_since_schedule",
        }
    )


def test_cron_job_status_with_running_job_and_previously_completed_job() -> None:
    """Test that checks state and metrics for a running job and previously completed job"""
    latest_job = CronJobLatestJobFactory.build(
        status=JobStatusFactory.build(
            conditions=[],
            start_time=1,
        ),
        pods=[JobPodFactory.build(lifecycle=kube.PodLifeCycle(phase=kube.Phase.RUNNING))],
    )
    cron_job_status = CronJobStatusFactory.build(
        active_jobs_count=1,
        last_duration=1,
        last_successful_time=Timestamp(1.0),
        last_schedule_time=Timestamp(1.0),
    )

    check_result = list(
        kube_cronjob_status._check_cron_job_status(Timestamp(2.0), {}, cron_job_status, latest_job)
    )
    assert [r.state for r in check_result if isinstance(r, Result)] == [
        State.OK,
        State.OK,
        State.OK,
    ]
    assert {r.name for r in check_result if isinstance(r, Metric)} == {
        "kube_cron_job_status_job_duration",
        "kube_cron_job_status_last_duration",
        "kube_cron_job_status_active",
        "kube_cron_job_status_since_completion",
        "kube_cron_job_status_since_schedule",
    }


def test_cron_job_status_last_duration() -> None:
    """Test that check outputs duration metric"""
    duration_value = 10
    cron_job_status = CronJobStatusFactory.build(last_duration=duration_value)
    latest_job = CronJobLatestJobFactory.build()

    check_result = list(
        kube_cronjob_status._check_cron_job_status(Timestamp(2.0), {}, cron_job_status, latest_job)
    )

    assert [
        r
        for r in check_result
        if isinstance(r, Metric) and r.name == "kube_cron_job_status_last_duration"
    ] == [Metric(name="kube_cron_job_status_last_duration", value=duration_value)]


def test_cron_job_status_with_failed_job() -> None:
    """Test that check outputs CRIT state and reason message when latest job fails"""
    cron_job_status = CronJobStatusFactory.build()
    failure_reason = "reason"
    waiting_container = _mocked_container_info_from_state(
        state=kube.ContainerWaitingState(reason=failure_reason, detail="detail")
    )
    latest_job = CronJobLatestJobFactory.build(
        pods=[
            JobPodFactory.build(
                containers={waiting_container.container_id: waiting_container}, init_containers={}
            )
        ],
        status=JobStatusFactory.build(
            conditions=[
                JobConditionFactory.build(
                    type_=kube.JobConditionType.FAILED, status=kube.ConditionStatus.TRUE
                )
            ]
        ),
    )

    check_result = list(
        kube_cronjob_status._check_cron_job_status(Timestamp(2.0), {}, cron_job_status, latest_job)
    )
    status_check_result = check_result[0]
    assert isinstance(status_check_result, Result)
    assert status_check_result.state == State.CRIT
    assert status_check_result.summary == f"Latest job: Failed ({failure_reason})"
