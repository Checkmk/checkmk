#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import json
import time
from typing import Any, Iterable, Mapping, Sequence, Tuple

from typing_extensions import assert_never

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    IgnoreResultsError,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import (
    ConditionStatus,
    CronJobLatestJob,
    CronJobStatus,
    JobCondition,
    JobConditionType,
    JobPod,
    Phase,
    pod_status_message,
    Timestamp,
)


class JobStatusType(enum.Enum):
    COMPLETED = "Completed"
    RUNNING = "Running"
    PENDING = "Pending"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


def parse_cron_job_status(string_table: StringTable) -> CronJobStatus:
    return CronJobStatus(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_cron_job_status_v1",
    parsed_section_name="kube_cron_job_status",
    parse_function=parse_cron_job_status,
)


def parse_latest_job(string_table: StringTable) -> CronJobLatestJob:
    return CronJobLatestJob(**json.loads(string_table[0][0]))


register.agent_section(
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

    if len(latest_job.pods) != 1:
        raise ValueError("Job doesn't have one pod")

    job_pod = latest_job.pods[0]
    job_status = _determine_job_status(latest_job.status.conditions, job_pod)

    yield from _cron_job_status(
        current_time=current_time,
        pending_levels=params.get("status_pending"),
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

    if status.last_duration:
        yield Metric(name="kube_cron_job_status_last_duration", value=status.last_duration)

    if status.active_jobs_count is not None:
        yield Metric(name="kube_cron_job_status_active", value=status.active_jobs_count)


def _determine_job_status(job_conditions: Sequence[JobCondition], job_pod: JobPod) -> JobStatusType:

    if job_conditions:
        for condition in job_conditions:
            if (
                condition.type_ is JobConditionType.COMPLETE
                and condition.status == ConditionStatus.TRUE
            ):
                return JobStatusType.COMPLETED
            if (
                condition.type_ is JobConditionType.FAILED
                and condition.status == ConditionStatus.TRUE
            ):
                return JobStatusType.FAILED

    if job_pod.lifecycle.phase is Phase.RUNNING:
        return JobStatusType.RUNNING

    if job_pod.lifecycle.phase is Phase.PENDING:
        return JobStatusType.PENDING

    return JobStatusType.UNKNOWN


def _cron_job_status(
    current_time: Timestamp,
    pending_levels: Tuple[int, int] | None,
    job_status: JobStatusType,
    job_pod: JobPod,
    job_start_time: Timestamp | None,
) -> Iterable[Result]:
    if job_start_time is None:
        return Result(state=State.UNKNOWN, summary="Latest job: Suspended")

    match job_status:
        case JobStatusType.COMPLETED:
            state = State.OK
            status_message = "Completed"
        case JobStatusType.FAILED:
            state = State.CRIT
            status_message = f"Failed ({pod_status_message(pod_containers=list(job_pod.containers.values()), pod_init_containers=list(job_pod.init_containers.values()), section_kube_pod_lifecycle=job_pod.lifecycle)})"
        case JobStatusType.PENDING:
            non_running_time = current_time - job_start_time
            result = list(
                check_levels(
                    non_running_time,
                    render_func=render.timespan,
                    levels_upper=pending_levels,
                )
            )[0]
            state = result.state
            status_message = f"Pending since {result.summary}"
        case JobStatusType.RUNNING:
            state = State.OK
            status_message = f"Running since {render.timespan(time.time() - job_start_time)}"
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

    yield from check_levels(
        current_time - last_successful_time,
        metric_name="kube_cron_job_status_since_completion",
        label="Time since last successful completion",
        render_func=render.timespan,
    )


def _last_schedule(current_time: Timestamp, last_schedule_time: Timestamp | None) -> CheckResult:
    if last_schedule_time is None:
        yield Result(state=State.OK, summary="Job is yet to be scheduled")
        return

    yield from check_levels(
        current_time - last_schedule_time,
        metric_name="kube_cron_job_status_since_schedule",
        label="Time since last schedule",
        render_func=render.timespan,
    )


register.check_plugin(
    name="kube_cronjob_status",
    service_name="Status",
    sections=["kube_cron_job_status", "kube_cron_job_latest_job"],
    discovery_function=discovery_cron_job_status,
    check_function=check_cron_job_status,
    check_ruleset_name="kube_cronjob_status",
    check_default_parameters={},
)
