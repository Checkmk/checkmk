#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import threading
from collections.abc import Sequence
from contextlib import nullcontext
from pathlib import Path

import pytest

from cmk.automations.internal import AutomationID
from cmk.ccc import store
from cmk.ccc import version as cmk_version
from cmk.gui.background_job.job import BackgroundProcessInterface
from cmk.gui.http import request
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib import automation_background_job
from cmk.gui.watolib.automation_background_job import (
    AutomationCheckmkAutomationGetStatus,
    AutomationCheckmkAutomationStart,
    AutomationCheckmkAutomationStartRequest,
    CheckmkAutomationBackgroundJob,
)
from cmk.gui.watolib.automations import CheckmkAutomationRequest
from cmk.livestatus_client import SiteConfigurations
from cmk.ruleset_matcher.tags import TagConfigSpec

RESULT: object = None


class TestCheckmkAutomationBackgroundJob:
    @staticmethod
    def _mock_save(_path: object, data: object, **kwargs: object) -> None:  # noqa: ARG004
        global RESULT
        RESULT = data

    @pytest.fixture(name="save_text_to_file")
    def save_text_to_file_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(store, "save_text_to_file", self._mock_save)

    @staticmethod
    def _check_mk_local_automation_serialized(
        *, for_cmk_version: str, **_kwargs: object
    ) -> tuple[Sequence[str], str]:
        return (
            ["x", "y", "z"],
            f"result for {for_cmk_version}",
        )

    @staticmethod
    def _api_request() -> CheckmkAutomationRequest:
        return CheckmkAutomationRequest(
            command=AutomationID("test"),
            args=None,
            indata=None,
            stdin_data=None,
            timeout=None,
        )

    @pytest.fixture(name="check_mk_local_automation_serialized")
    def check_mk_local_automation_serialized_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            automation_background_job,
            "check_mk_local_automation_serialized",
            self._check_mk_local_automation_serialized,
        )

    @pytest.mark.usefixtures(
        "check_mk_local_automation_serialized",
        "save_text_to_file",
        "request_context",
    )
    def test_execute_automation(self) -> None:
        """
        Test the most inner logic of the job

        The result is serialized for the provided version and stored as is
        """
        api_request = self._api_request()
        job = CheckmkAutomationBackgroundJob("job_id")
        os.makedirs(job.get_work_dir())
        with open(os.devnull, "w") as progress_update:
            job._execute_automation(  # noqa: SLF001
                BackgroundProcessInterface(
                    job.get_work_dir(),
                    "job_id",
                    logging.getLogger(),
                    threading.Event(),
                    lambda x: nullcontext(),  # noqa: ARG005
                    progress_update,
                ),
                api_request,
                cmk_version.Version.from_str("2.4.0p1"),
                dict,
            )
        assert RESULT == "result for 2.4.0p1"

    @pytest.mark.parametrize(
        ["version", "result"],
        [
            pytest.param(None, "result for 1.6.0p1", id="Missing version header"),
            pytest.param("2.4.0p1", "result for 2.4.0p1", id="Version header"),
        ],
    )
    @pytest.mark.usefixtures(
        "patch_omd_site",
        "allow_background_jobs",
        "request_context",
        "check_mk_local_automation_serialized",
    )
    def test_automation_commands(
        self, version: str | None, result: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Test the execution of the whole background job

        Assert that the version of the central site gets passed correctly
        """
        with monkeypatch.context() as m:
            if version is not None:
                m.setattr(request, "headers", {"x-checkmk-version": version})

            automation = AutomationCheckmkAutomationStart()
            job_id = automation.execute(
                AutomationCheckmkAutomationStartRequest(
                    api_request=self._api_request(),
                    user_permission_config=UserPermissionSerializableConfig(
                        roles={}, user_roles={}, default_user_profile_roles=[]
                    ),
                    site_configs=SiteConfigurations({}),
                    wato_hide_folders_without_read_permissions=False,
                    wato_host_attrs=[],
                    tags=TagConfigSpec(tag_groups=[], aux_tags=[]),
                )
            )
            job = CheckmkAutomationBackgroundJob(job_id)
            job.wait_for_completion(10)
            job_result = AutomationCheckmkAutomationGetStatus._load_result(  # noqa: SLF001
                Path(job.get_work_dir()) / "result.mk"
            )
            assert job_result == result
