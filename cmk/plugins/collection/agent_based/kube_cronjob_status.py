#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import time
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, assert_never

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.kube.schemata.api import (
    ConditionStatus,
    ContainerStateType,
    JobCondition,
    JobConditionType,
    Phase,
    Timestamp,
)
from cmk.plugins.kube.schemata.section import CronJobLatestJob, CronJobStatus, JobPod
from cmk.plugins.lib.kube import get_age_levels_for, pod_status_message

CRONJOB_DEFAULT_PARAMS: Mapping[str, Any] = {
    "pending": ("levels", (300, 600)),
}


class JobStatusType(enum.Enum):
    COMPLETED = "Completed"
    RUNNING = "Running"
    PENDING = "Pending"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


def parse_cron_job_status(string_table: StringTable) -> CronJobStatus:
    return CronJobStatus.model_validate_json(string_table[0][0])


agent_section_kube_cron_job_status_v1 = AgentSection(
    name="kube_cron_job_status_v1",
    parsed_section_name="kube_cron_job_status",
    parse_function=parse_cron_job_status,
)


def parse_latest_job(string_table: StringTable) -> CronJobLatestJob:
    return CronJobLatestJob.model_validate_json(string_table[0][0])


agent_section_kube_cron_job_latest_job_v1 = AgentSection(
    name="kube_cron_job_latest_job_v1",
    parsed_section_name="kube_cron_job_latest_job",
    parse_function=parse_latest_job,
)


def discovery_cron_job_status(
    section_kube_cron_job_status: CronJobStatus | None,
    section_kube_cron_job_latest_job: CronJobLatestJob | None,
) -> DiscoveryResult:
    yield Service()


def check_cron_job_status(
    params: Mapping[str, Any],
    section_kube_cron_job_status: CronJobStatus | None,
    section_kube_cron_job_latest_job: CronJobLatestJob | None,
) -> CheckResult:
    yield from _check_cron_job_status(
        Timestamp(time.time()),
        params,
        section_kube_cron_job_status,
        section_kube_cron_job_latest_job,
    )


def _check_cron_job_status(
    current_time: Timestamp,
    params: Mapping[str, Any],
    status: CronJobStatus | None,
    latest_job: CronJobLatestJob | None,
) -> CheckResult:
    if status is None:
        raise IgnoreResultsError("No Status information currently available")

    if latest_job is None:
        raise IgnoreResultsError("No Job has been scheduled")

    job_pod = latest_job.pods[0] if latest_job.pods else None
    job_status = _determine_job_status(latest_job.status.conditions, job_pod)

    yield from _cron_job_status(
        current_time=current_time,
        pending_levels=get_age_levels_for(params, "pending"),
        running_levels=get_age_levels_for(params, "running"),
        job_status=job_status,
        job_pod=job_pod,
        job_start_time=latest_job.status.start_time,
    )
    yield from _last_successful_completion(current_time, status.last_successful_time)
    yield from _last_schedule(current_time, status.last_schedule_time)

    # Also consider PENDING as part of the job's runtime
    if (
        job_status in (JobStatusType.PENDING, JobStatusType.RUNNING)
        and latest_job.status.start_time is not None
    ):
        yield Metric(
            name="kube_cron_job_status_job_duration",
            value=current_time - latest_job.status.start_time,
        )

    if job_status is JobStatusType.RUNNING and job_pod is not None:
        if (pod_running_start_time := _pod_running_start_time(job_pod)) is not None:
            yield Metric(
                name="kube_cron_job_status_execution_duration",
                value=current_time - pod_running_start_time,
            )

    if status.last_duration:
        yield Metric(name="kube_cron_job_status_last_duration", value=status.last_duration)

    if status.active_jobs_count is not None:
        yield Metric(name="kube_cron_job_status_active", value=status.active_jobs_count)


def _pod_running_start_time(pod: JobPod) -> int | None:
    """Determine the run start time of the pod

    Assumptions made:
        * we consider it to be running if all containers of the pod are running (this should be
        reflected in the pod phase)
        * the pod run start time is the start time of the last container to start running
    """
    latest_start_container_time = 0
    for container_status in pod.containers.values():
        if container_status.state.type is not ContainerStateType.running:
            return None
        latest_start_container_time = max(
            latest_start_container_time, container_status.state.start_time
        )
    return latest_start_container_time


def _determine_job_status(
    job_conditions: Sequence[JobCondition], job_pod: JobPod | None
) -> JobStatusType:
    if job_conditions:
        for condition in job_conditions:
            if (
                condition.type_ is JobConditionType.COMPLETE
                and condition.status == ConditionStatus.TRUE
            ):
                return JobStatusType.COMPLETED
            if (
                condition.type_ is JobConditionType.SUCCESS_CRITERIA_MET
                and condition.status == ConditionStatus.TRUE
            ):
                return JobStatusType.COMPLETED
            if (
                condition.type_ is JobConditionType.FAILURE_TARGET
                and condition.status == ConditionStatus.TRUE
            ):
                return JobStatusType.FAILED
            if (
                condition.type_ is JobConditionType.FAILED
                and condition.status == ConditionStatus.TRUE
            ):
                return JobStatusType.FAILED

    if job_pod is None:
        raise IgnoreResultsError("No Pod was scheduled, however the Job did not report failure.")

    if job_pod.lifecycle.phase is Phase.RUNNING:
        return JobStatusType.RUNNING

    if job_pod.lifecycle.phase is Phase.PENDING:
        return JobStatusType.PENDING

    return JobStatusType.UNKNOWN


def _cron_job_status(
    current_time: Timestamp,
    pending_levels: tuple[int, int] | None,
    running_levels: tuple[int, int] | None,
    job_status: JobStatusType,
    job_pod: JobPod | None,
    job_start_time: Timestamp | None,
) -> Iterable[Result]:
    if job_start_time is None:
        yield Result(state=State.UNKNOWN, summary="Latest job: Suspended")
        return

    match job_status:
        case JobStatusType.COMPLETED:
            state = State.OK
            status_message = "Completed"
        case JobStatusType.FAILED:
            state = State.CRIT
            if job_pod is None:
                status_message = "Failed with no pod"
            else:
                status_message = f"Failed ({pod_status_message(pod_containers=list(job_pod.containers.values()), pod_init_containers=list(job_pod.init_containers.values()), section_kube_pod_lifecycle=job_pod.lifecycle)})"
        case JobStatusType.PENDING:
            non_running_time = current_time - job_start_time
            result = list(
                check_levels_v1(
                    non_running_time,
                    render_func=render.timespan,
                    levels_upper=pending_levels,
                )
            )[0]
            state = result.state
            status_message = f"Pending since {result.summary}"
        case JobStatusType.RUNNING:
            result = list(
                check_levels_v1(
                    current_time - job_start_time,
                    render_func=render.timespan,
                    levels_upper=running_levels,
                )
            )[0]
            state = result.state
            status_message = f"Running since {result.summary}"
        case JobStatusType.UNKNOWN:
            raise ValueError("Unknown status type for latest job")
        case _:
            assert_never(job_status)

    yield Result(state=state, summary=f"Latest job: {status_message}")


def _last_successful_completion(
    current_time: Timestamp, last_successful_time: Timestamp | None
) -> CheckResult:
    if last_successful_time is None:
        yield Result(state=State.OK, summary="No successfully completed job")
        return

    yield from check_levels_v1(
        current_time - last_successful_time,
        metric_name="kube_cron_job_status_since_completion",
        label="Time since last successful completion",
        render_func=render.timespan,
    )


def _last_schedule(current_time: Timestamp, last_schedule_time: Timestamp | None) -> CheckResult:
    if last_schedule_time is None:
        yield Result(state=State.OK, summary="Job is yet to be scheduled")
        return

    yield from check_levels_v1(
        current_time - last_schedule_time,
        metric_name="kube_cron_job_status_since_schedule",
        label="Time since last schedule",
        render_func=render.timespan,
    )


check_plugin_kube_cronjob_status = CheckPlugin(
    name="kube_cronjob_status",
    service_name="Status",
    sections=["kube_cron_job_status", "kube_cron_job_latest_job"],
    discovery_function=discovery_cron_job_status,
    check_function=check_cron_job_status,
    check_ruleset_name="kube_cronjob_status",
    check_default_parameters=CRONJOB_DEFAULT_PARAMS,
)
