#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pytest_mock import MockerFixture

from tests.testlib.unit.rest_api_client import ClientRegistry


class TestBackgroundJobSnapshot:
    @pytest.mark.usefixtures("inline_background_jobs")
    def test_openapi_background_job_snapshot(
        self, base: str, clients: ClientRegistry, mocker: MockerFixture
    ) -> None:
        clients.HostConfig.create(host_name="foobar")

        automation = mocker.patch("cmk.gui.watolib.bulk_discovery.discovery")
        resp = clients.ServiceDiscovery.bulk_discovery(hostnames=["foobar"], follow_redirects=True)
        automation.assert_called_once()

        job_id = resp.json["id"]
        resp = clients.BackgroundJob.get(job_id=job_id)

        assert set(resp.json["extensions"]["status"]["log_info"].keys()) == {
            "JobProgressUpdate",
            "JobResult",
            "JobException",
        }
