#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import kube_cronjob_status
from cmk.plugins.kube.schemata.api import (
    ConditionStatus,
    ContainerRunningState,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    JobCondition,
    JobConditionType,
    Phase,
    Timestamp,
)
from cmk.plugins.kube.schemata.section import (
    CronJobLatestJob,
    CronJobStatus,
    JobPod,
    JobStatus,
    PodLifeCycle,
)


class JobPodFactory(ModelFactory):
    __model__ = JobPod


class ContainerStatusFactory(ModelFactory):
    __model__ = ContainerStatus


class ContainerWaitingStateFactory(ModelFactory):
    __model__ = ContainerWaitingState


class ContainerRunningStateFactory(ModelFactory):
    __model__ = ContainerRunningState


class JobConditionFactory(ModelFactory):
    __model__ = JobCondition


class JobStatusFactory(ModelFactory):
    __model__ = JobStatus

    conditions = [JobCondition(type_=JobConditionType.COMPLETE, status=ConditionStatus.TRUE)]
    start_time = Timestamp(1.0)


class CronJobLatestJobFactory(ModelFactory):
    __model__ = CronJobLatestJob

    status = JobStatusFactory.build()
    pods = JobPodFactory.batch(size=1)


class CronJobStatusFactory(ModelFactory):
    __model__ = CronJobStatus

    last_successful_time = Timestamp(1.0)
    last_schedule_time = Timestamp(1.0)


def _mocked_container_info_from_state(
    state: ContainerRunningState | ContainerTerminatedState | ContainerWaitingState,
) -> ContainerStatus:
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
        pods=[
            JobPodFactory.build(
                lifecycle=PodLifeCycle(phase=Phase.RUNNING),
                containers={
                    "running": ContainerStatusFactory.build(
                        ready=True, state=ContainerRunningStateFactory.build()
                    )
                },
            )
        ],
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
        "kube_cron_job_status_execution_duration",
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
        state=ContainerWaitingState(reason=failure_reason, detail="detail")
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
                    type_=JobConditionType.FAILED, status=ConditionStatus.TRUE
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


def test_cron_job_status_with_pending_job() -> None:
    """Test that check outputs WARN state when latest job is pending and crosses the threshold"""
    result = list(
        kube_cronjob_status._cron_job_status(
            current_time=Timestamp(300.0),
            pending_levels=(300, 600),
            running_levels=None,
            job_status=kube_cronjob_status.JobStatusType.PENDING,
            job_pod=JobPodFactory.build(),
            job_start_time=Timestamp(0.0),
        )
    )[0]
    assert result.state == State.WARN


def test_kube_cron_job_with_running_params() -> None:
    current_time = 10.0
    elapsed_running_time = 8.0
    warn, crit = 8, 10

    result = list(
        kube_cronjob_status._cron_job_status(
            current_time=Timestamp(current_time),
            pending_levels=None,
            running_levels=(warn, crit),
            job_status=kube_cronjob_status.JobStatusType.RUNNING,
            job_pod=JobPodFactory.build(),
            job_start_time=Timestamp(current_time - elapsed_running_time),
        )
    )[0]

    assert result.state == State.WARN
    assert result.summary.startswith("Latest job: Running since")


def test_kube_cronjob_with_no_pod() -> None:
    # Some jobs have a condition like this (CMK-12592)
    # "type": "Failed", "reason":"DeadlineExceeded","message":"Job was active longer than specified deadline"
    current_time = 10.0
    elapsed_running_time = 8.0

    result = list(
        kube_cronjob_status._cron_job_status(
            current_time=Timestamp(current_time),
            pending_levels=None,
            running_levels=None,
            job_status=kube_cronjob_status.JobStatusType.FAILED,
            job_pod=None,
            job_start_time=Timestamp(current_time - elapsed_running_time),
        )
    )[0]

    assert result.state == State.CRIT
    assert result.summary == "Latest job: Failed with no pod"


def test_cron_job_status_with_failed_target_job() -> None:
    cron_job_status = CronJobStatusFactory.build()
    failure_reason = "reason"
    waiting_container = _mocked_container_info_from_state(
        state=ContainerWaitingState(reason=failure_reason, detail="detail")
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
                    type_=JobConditionType.FAILURE_TARGET, status=ConditionStatus.TRUE
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


def test_cron_job_status_with_success_criteria_met_job() -> None:
    cron_job_status = CronJobStatusFactory.build()
    failure_reason = "reason"
    waiting_container = _mocked_container_info_from_state(
        state=ContainerWaitingState(reason=failure_reason, detail="detail")
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
                    type_=JobConditionType.SUCCESS_CRITERIA_MET, status=ConditionStatus.TRUE
                )
            ]
        ),
    )

    check_result = list(
        kube_cronjob_status._check_cron_job_status(Timestamp(2.0), {}, cron_job_status, latest_job)
    )
    status_check_result = check_result[0]
    assert isinstance(status_check_result, Result)
    assert status_check_result.state == State.OK
    assert status_check_result.summary == "Latest job: Completed"
