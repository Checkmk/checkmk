import datetime
import json

from kubernetes import client  # type: ignore[import]
from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import (
    parse_cron_job_spec,
    parse_cron_job_status,
    parse_metadata,
)


class TestAPICronJob:
    def test_parse_metadata(self) -> None:
        node_raw_metadata = {
            "name": "cronjob",
            "namespace": "default",
            "creation_timestamp": datetime.datetime.strptime(
                "2021-05-04T09:01:13Z", "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=datetime.timezone.utc),
            "uid": "uid",
        }
        metadata_obj = client.V1ObjectMeta(**node_raw_metadata)
        metadata = parse_metadata(metadata_obj, type_=str)
        assert metadata.name == "cronjob"
        assert metadata.namespace is not None

    def test_parse_cron_job_spec(self, dummy_host: str, batch_client: client.BatchV1Api) -> None:
        cron_job_list_with_info = {
            "items": [
                {
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
                },
            ],
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/batch/v1/cronjobs",
            body=json.dumps(cron_job_list_with_info),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            cron_job = list(batch_client.list_cron_job_for_all_namespaces().items)[0]
        spec = parse_cron_job_spec(cron_job.spec)
        assert isinstance(spec.concurrency_policy, api.ConcurrencyPolicy)
        assert spec.schedule is not None
        assert spec.schedule == "*/5 * * * *"

    def test_parse_cron_job_status(self, dummy_host: str, batch_client: client.BatchV1Api) -> None:
        cron_job_list_with_info = {
            "items": [
                {
                    "status": {
                        "active": None,
                        "last_schedule_time": None,
                        "last_successful_time": None,
                    }
                },
            ],
        }
        Entry.single_register(
            Entry.GET,
            f"{dummy_host}/apis/batch/v1/cronjobs",
            body=json.dumps(cron_job_list_with_info),
            headers={"content-type": "application/json"},
        )
        with Mocketizer():
            cron_job = list(batch_client.list_cron_job_for_all_namespaces().items)[0]
        status = parse_cron_job_status(cron_job.status)
        assert status == api.CronJobStatus(
            active=None, last_schedule_time=None, last_successful_time=None
        )
