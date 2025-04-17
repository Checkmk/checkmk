#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence

from cmk.plugins.kube.agent_handlers.common import (
    AnnotationOption,
    CheckmkHostSettings,
    collect_cpu_resources_from_api_pods,
    collect_memory_resources_from_api_pods,
    filter_annotations_by_key_pattern,
    pod_lifecycle_phase,
    pod_resources_from_api_pods,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import api, section


def create_api_sections(
    api_cronjob: api.CronJob,
    cronjob_pods: Sequence[api.Pod],
    timestamp_sorted_jobs: Sequence[api.Job],
    host_settings: CheckmkHostSettings,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cron_job_info_v1"),
            section=_info(
                api_cronjob,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cron_job_status_v1"),
            section=_status(
                api_cronjob.status,
                timestamp_sorted_jobs,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=pod_resources_from_api_pods(cronjob_pods),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=collect_memory_resources_from_api_pods(cronjob_pods),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=collect_cpu_resources_from_api_pods(cronjob_pods),
        ),
    )

    if len(timestamp_sorted_jobs):
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cron_job_latest_job_v1"),
            section=_latest_job(timestamp_sorted_jobs[-1], {pod.uid: pod for pod in cronjob_pods}),
        )


def _info(
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


def _status(
    cronjob_status: api.CronJobStatus,
    timestamp_sorted_jobs: Sequence[api.Job],
) -> section.CronJobStatus:
    return section.CronJobStatus(
        active_jobs_count=len(cronjob_status.active) if cronjob_status.active else None,
        last_duration=(
            _calculate_job_duration(last_completed_job)
            if (last_completed_job := _retrieve_last_completed_job(timestamp_sorted_jobs))
            is not None
            else None
        ),
        last_successful_time=cronjob_status.last_successful_time,
        last_schedule_time=cronjob_status.last_schedule_time,
    )


def _latest_job(job: api.Job, pods: Mapping[api.PodUID, api.Pod]) -> section.CronJobLatestJob:
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
