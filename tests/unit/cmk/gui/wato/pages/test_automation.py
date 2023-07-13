#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException

from cmk.automations.results import ABCAutomationResult, ResultTypeRegistry, SerializedResult

from cmk.gui.http import request, response
from cmk.gui.wato.pages import automation
from cmk.gui.watolib.utils import mk_repr


@dataclass
class ResultTest(ABCAutomationResult):
    field_1: tuple[int, int]
    field_2: str | None

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return (
            self._default_serialize()
            if for_cmk_version >= cmk_version.Version("2.2.0i1")
            else SerializedResult(repr((self.field_1,)))
        )

    @staticmethod
    def automation_call() -> str:
        return "test"


class TestModeAutomation:
    @pytest.fixture(name="result_type_registry")
    def result_type_registry_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        registry = ResultTypeRegistry()
        registry.register(ResultTest)
        monkeypatch.setattr(
            automation,
            "result_type_registry",
            registry,
        )

    @staticmethod
    def _check_mk_local_automation_serialized(  # type:ignore[no-untyped-def]
        **_kwargs,
    ) -> tuple[Sequence[str], str]:
        return (
            ["x", "y", "z"],
            "((1, 2), 'abc')",
        )

    @pytest.fixture(name="check_mk_local_automation_serialized")
    def check_mk_local_automation_serialized_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            automation,
            "check_mk_local_automation_serialized",
            self._check_mk_local_automation_serialized,
        )

    @pytest.fixture(name="patch_edition")
    def patch_edition_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(cmk_version, "edition", lambda: cmk_version.Edition.CEE)

    @pytest.fixture(name="setup_request")
    def setup_request_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(automation, "_get_login_secret", lambda **_kwargs: "secret")
        request.set_var("secret", "secret")
        request.set_var("command", "checkmk-automation")
        request.set_var("automation", "test")
        request.set_var("arguments", mk_repr(None).decode())
        request.set_var("indata", mk_repr(None).decode())
        request.set_var("stdin_data", mk_repr(None).decode())
        request.set_var("timeout", mk_repr(None).decode())

    @pytest.mark.usefixtures(
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "setup_request",
        "patch_edition",
    )
    def test_execute_cmk_automation_current_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            request,
            "headers",
            {"x-checkmk-version": cmk_version.__version__, "x-checkmk-edition": "cee"},
        )
        automation.ModeAutomation()._execute_cmk_automation()
        assert response.get_data() == b"((1, 2), 'abc')"

    @pytest.mark.usefixtures(
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "setup_request",
        "patch_edition",
    )
    def test_execute_cmk_automation_previous_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            request,
            "headers",
            {"x-checkmk-version": "2.1.0p31", "x-checkmk-edition": "cee"},
        )
        automation.ModeAutomation()._execute_cmk_automation()
        assert response.get_data() == b"((1, 2),)"

    @pytest.mark.parametrize(
        "incomp_version",
        [
            "1.6.0p23",  # very old major
            "10.0.0",  # newer major
        ],
    )
    @pytest.mark.usefixtures(
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "setup_request",
        "patch_edition",
    )
    def test_execute_cmk_automation_incompatible(  # type:ignore[no-untyped-def]
        self, incomp_version: str, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            request,
            "headers",
            {"x-checkmk-version": incomp_version, "x-checkmk-edition": "cee"},
        )
        with pytest.raises(MKGeneralException, match="not compatible"):
            automation.ModeAutomation()._execute_cmk_automation()
