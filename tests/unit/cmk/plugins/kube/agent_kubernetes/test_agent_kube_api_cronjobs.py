#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

from kubernetes import client  # type: ignore[import-untyped]

from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform import parse_cron_job_spec, parse_cron_job_status, parse_metadata
from tests.unit.cmk.plugins.kube.agent_kubernetes.utils import FakeResponse


class TestAPICronJob:
    def test_parse_metadata(self) -> None:
        node_raw_metadata = {
            "name": "cronjob",
            "namespace": "default",
            "creation_timestamp": datetime.datetime.strptime(
                "2021-05-04T09:01:13Z", "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=datetime.UTC),
            "uid": "uid",
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        metadata = parse_metadata(metadata_obj)
        assert metadata.name == "cronjob"
        assert metadata.namespace is not None

    def test_parse_cron_job_spec(self, dummy_host: str, batch_client: client.BatchV1Api) -> None:
        cron_job_list_with_info = {
            "spec": {
                "schedule": "*/5 * * * *",
                "concurrencyPolicy": "Allow",
                "failedJobsHistoryLimit": 10,
                "successfulJobsHistoryLimit": 10,
                "suspend": False,
                "jobTemplate": {
                    "metadata": {},
                    "spec": {
                        "template": {
                            "metadata": {},
                            "spec": {"containers": []},
                        },
                    },
                },
            },
        }
        cron_job = batch_client.api_client.deserialize(
            FakeResponse(cron_job_list_with_info),
            "V1CronJob",
        )
        spec = parse_cron_job_spec(cron_job.spec)
        assert isinstance(spec.concurrency_policy, api.ConcurrencyPolicy)
        assert spec.schedule is not None
        assert spec.schedule == "*/5 * * * *"

    def test_parse_cron_job_status(self, dummy_host: str, batch_client: client.BatchV1Api) -> None:
        cron_job_list_with_info = {
            "status": {
                "active": None,
                "last_schedule_time": None,
                "last_successful_time": None,
            }
        }
        cron_job = batch_client.api_client.deserialize(
            FakeResponse(cron_job_list_with_info),
            "V1CronJob",
        )
        status = parse_cron_job_status(cron_job.status)
        assert status == api.CronJobStatus(
            active=None, last_schedule_time=None, last_successful_time=None
        )
