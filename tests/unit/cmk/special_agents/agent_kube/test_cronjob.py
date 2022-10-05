#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section


class CronJobStatusFactory(ModelFactory):
    __model__ = api.CronJobStatus


class JobStatusFactory(ModelFactory):
    __model__ = api.JobStatus


class JobFactory(ModelFactory):
    __model__ = api.Job


class PodFactory(ModelFactory):
    __model__ = api.Pod


def test_cron_job_status_section() -> None:
    api_job = JobFactory.build(
        status=JobStatusFactory.build(
            start_time=api.Timestamp(1.0),
            completion_time=api.Timestamp(2.0),
        )
    )
    api_cron_job_status = CronJobStatusFactory.build(
        active=[api_job.uid],
        last_schedule_time=api.Timestamp(1.0),
        last_successful_time=api.Timestamp(2.0),
    )

    cron_job_status = agent.cron_job_status(api_cron_job_status, [api_job])

    assert cron_job_status == section.CronJobStatus(
        active_jobs_count=1,
        last_duration=1.0,
        last_schedule_time=api.Timestamp(1.0),
        last_successful_time=api.Timestamp(2.0),
    )


def test_cron_job_latest_job_section() -> None:
    pod_number = 1
    api_pods = PodFactory.batch(size=pod_number)
    api_job = JobFactory.build(
        status=JobStatusFactory.build(
            conditions=[],
            start_time=api.Timestamp(1.0),
            completion_time=None,
        ),
        pod_uids=[pod.uid for pod in api_pods],
    )

    latest_job = agent.cron_job_latest_job(api_job, {pod.uid: pod for pod in api_pods})

    assert len(latest_job.pods) == pod_number
    assert latest_job.status == section.JobStatus(
        conditions=[],
        start_time=api.Timestamp(1.0),
        completion_time=None,
    )
