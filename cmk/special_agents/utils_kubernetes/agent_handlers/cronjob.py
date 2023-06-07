#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

from cmk.special_agents.utils_kubernetes.agent_handlers.common import (
    AnnotationOption,
    filter_annotations_by_key_pattern,
    pod_lifecycle_phase,
)
from cmk.special_agents.utils_kubernetes.schemata import api, section


def info(
    cron_job: api.CronJob,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.CronJobInfo:
    return section.CronJobInfo(
        name=cron_job.metadata.name,
        namespace=cron_job.metadata.namespace,
        creation_timestamp=cron_job.metadata.creation_timestamp,
        labels=cron_job.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            cron_job.metadata.annotations, annotation_key_pattern
        ),
        schedule=cron_job.spec.schedule,
        concurrency_policy=cron_job.spec.concurrency_policy,
        failed_jobs_history_limit=cron_job.spec.failed_jobs_history_limit,
        successful_jobs_history_limit=cron_job.spec.successful_jobs_history_limit,
        suspend=cron_job.spec.suspend,
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def status(
    cronjob_status: api.CronJobStatus,
    timestamp_sorted_jobs: Sequence[api.Job],
) -> section.CronJobStatus:
    return section.CronJobStatus(
        active_jobs_count=len(cronjob_status.active) if cronjob_status.active else None,
        last_duration=_calculate_job_duration(last_completed_job)
        if (last_completed_job := _retrieve_last_completed_job(timestamp_sorted_jobs)) is not None
        else None,
        last_successful_time=cronjob_status.last_successful_time,
        last_schedule_time=cronjob_status.last_schedule_time,
    )


def latest_job(job: api.Job, pods: Mapping[api.PodUID, api.Pod]) -> section.CronJobLatestJob:
    return section.CronJobLatestJob(
        status=section.JobStatus(
            conditions=job.status.conditions or [],
            start_time=job.status.start_time,
            completion_time=job.status.completion_time,
        ),
        pods=[
            section.JobPod(
                init_containers=pod.init_containers,
                containers=pod.containers,
                lifecycle=pod_lifecycle_phase(pod.status),
            )
            for pod_uid in job.pod_uids
            if (pod := pods.get(pod_uid)) is not None
        ],
    )


def _retrieve_last_completed_job(jobs: Sequence[api.Job]) -> api.Job | None:
    for job in jobs:
        if job.status.completion_time is not None:
            return job
    return None


def _calculate_job_duration(job: api.Job) -> float | None:
    if job.status.completion_time is None or job.status.start_time is None:
        return None

    return job.status.completion_time - job.status.start_time
