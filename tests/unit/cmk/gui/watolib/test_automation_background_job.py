#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import threading
from collections.abc import Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from cmk.automations.results import ABCAutomationResult, ResultTypeRegistry, SerializedResult
from cmk.ccc import store
from cmk.ccc import version as cmk_version
from cmk.gui.background_job import BackgroundProcessInterface
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

RESULT: object = None


@dataclass
class ResultTest(ABCAutomationResult):
    field_1: int
    field_2: str | None

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return (
            self._default_serialize()
            if for_cmk_version >= cmk_version.Version.from_str("2.2.0i1")
            else SerializedResult("i was very different previously")
        )

    @staticmethod
    def automation_call() -> str:
        return "test"


class TestCheckmkAutomationBackgroundJob:
    @staticmethod
    def _mock_save(_path: Any, data: object, **kwargs: Any) -> None:
        global RESULT
        RESULT = data

    @pytest.fixture(name="save_text_to_file")
    def save_text_to_file_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(store, "save_text_to_file", self._mock_save)

    @pytest.fixture(name="result_type_registry")
    def result_type_registry_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        registry = ResultTypeRegistry()
        registry.register(ResultTest)
        monkeypatch.setattr(
            automation_background_job,
            "result_type_registry",
            registry,
        )

    @staticmethod
    def _check_mk_local_automation_serialized(
        **_kwargs: object,
    ) -> tuple[Sequence[str], str]:
        return (
            ["x", "y", "z"],
            "(2, None)",
        )

    @staticmethod
    def _api_request() -> CheckmkAutomationRequest:
        return CheckmkAutomationRequest(
            command="test",
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

    @pytest.mark.parametrize(
        ["version", "expected_result"],
        [
            pytest.param("2.1.0p10", "i was very different previously", id="old version"),
            pytest.param("2.2.0i1", "(2, None)", id="first version with new serialization"),
            pytest.param("2.5.0b1", "(2, None)", id="current version with new serialization"),
        ],
    )
    @pytest.mark.usefixtures(
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "save_text_to_file",
    )
    def test_execute_automation(
        self, version: str, expected_result: str, request_context: None
    ) -> None:
        """
        Test the most inner logic of the job

        The serialized output is expected to depend on the provided version
        """
        api_request = self._api_request()
        job = CheckmkAutomationBackgroundJob("job_id")
        os.makedirs(job.get_work_dir())
        job._execute_automation(
            BackgroundProcessInterface(
                job.get_work_dir(),
                "job_id",
                logging.getLogger(),
                threading.Event(),
                lambda x: nullcontext(),
                open(os.devnull, "w"),
            ),
            api_request,
            cmk_version.Version.from_str(version),
            lambda: {},
        )
        assert RESULT == expected_result

    @pytest.mark.parametrize(
        ["version", "result"],
        [
            pytest.param(None, "i was very different previously", id="Missing version header"),
            pytest.param(
                "2.1.0p10",
                "i was very different previously",
                id="Old version with old serialization",
            ),
            pytest.param("2.2.0i1", "(2, None)", id="First version with new serialization"),
            pytest.param("2.5.0b1", "(2, None)", id="Latest version with new serialization"),
        ],
    )
    @pytest.mark.usefixtures(
        "patch_omd_site",
        "allow_background_jobs",
        "request_context",
        "result_type_registry",
        "check_mk_local_automation_serialized",
    )
    def test_automation_commands(
        self, version: str | None, result: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Test the execution of the whole background job

        Assert that the version gets passed correctly
        and that the result serialization depends on that version
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
                )
            )
            job = CheckmkAutomationBackgroundJob(job_id)
            job.wait_for_completion(10)
            job_result = AutomationCheckmkAutomationGetStatus._load_result(
                Path(job.get_work_dir()) / "result.mk"
            )
            assert job_result == result
