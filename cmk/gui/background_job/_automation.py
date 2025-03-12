#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import override

from cmk.gui.background_job import BackgroundJob
from cmk.gui.http import request
from cmk.gui.watolib.automation_commands import AutomationCommand

JOB_ID = str


class AutomationBackgroundJobSnapshot(AutomationCommand[JOB_ID]):
    """Fetch the background job snapshot from a remote site"""

    @override
    def command_name(self) -> str:
        return "fetch-background-job-snapshot"

    @override
    def get_request(self) -> str:
        return request.get_validated_type_input_mandatory(str, "job_id")

    @override
    def execute(self, api_request: JOB_ID) -> str:
        job = BackgroundJob(api_request)
        return json.dumps(job.get_status_snapshot().to_dict())
