#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple
from unittest.mock import MagicMock

import pytest

from cmk.automations.results import ABCAutomationResult, ResultTypeRegistry

from cmk.gui.watolib import automations

RESULT: object = None


@dataclass
class ResultTest(ABCAutomationResult):
    field_1: int
    field_2: Optional[str]

    def to_pre_21(self) -> Tuple[int, Optional[str]]:
        return (
            self.field_1,
            self.field_2,
        )

    @staticmethod
    def automation_call() -> str:
        return "test"


class TestCheckmkAutomationBackgroundJob:
    @staticmethod
    def _mock_save(_path: Any, data: object, **kwargs: Any) -> None:
        global RESULT
        RESULT = data

    @pytest.fixture(name="save_object_to_file")
    def save_object_to_file_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            automations.store,
            "save_object_to_file",
            self._mock_save,
        )

    @pytest.fixture(name="save_text_to_file")
    def save_text_to_file_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            automations.store,
            "save_text_to_file",
            self._mock_save,
        )

    @pytest.fixture(name="result_type_registry")
    def result_type_registry_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        registry = ResultTypeRegistry()
        registry.register(ResultTest)
        monkeypatch.setattr(
            automations,
            "result_type_registry",
            registry,
        )

    @staticmethod
    def _check_mk_local_automation_serialized(**_kwargs) -> Tuple[Sequence[str], str]:
        return (
            ["x", "y", "z"],
            "(2, None)",
        )

    @pytest.fixture(name="check_mk_local_automation_serialized")
    def check_mk_local_automation_serialized_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            automations,
            "check_mk_local_automation_serialized",
            self._check_mk_local_automation_serialized,
        )

    @pytest.mark.usefixtures(
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "save_text_to_file",
    )
    def test_execute_automation_post_21(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            automations.request,
            "headers",
            {"x-checkmk-version": "2.1.0i1"},
        )
        automations.CheckmkAutomationBackgroundJob(
            "job_id",
            api_request := automations.CheckmkAutomationRequest(
                command="test",
                args=None,
                indata=None,
                stdin_data=None,
                timeout=None,
            ),
        ).execute_automation(
            MagicMock(),
            api_request,
        )
        assert RESULT == "(2, None)"

    @pytest.mark.parametrize("set_version", [True, False])
    @pytest.mark.usefixtures(
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "save_object_to_file",
    )
    def test_execute_automation_pre_21(
        self, set_version: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if set_version:
            monkeypatch.setattr(
                automations.request,
                "headers",
                {"x-checkmk-version": "2.0.0p10"},
            )

        automations.CheckmkAutomationBackgroundJob(
            "job_id",
            api_request := automations.CheckmkAutomationRequest(
                command="test",
                args=None,
                indata=None,
                stdin_data=None,
                timeout=None,
            ),
        ).execute_automation(
            MagicMock(),
            api_request,
        )
        assert RESULT == (2, None)
