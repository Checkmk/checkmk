#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import ast
from collections.abc import Sequence
from dataclasses import dataclass

import pytest
from flask import Flask

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

from cmk.utils import paths
from cmk.utils.local_secrets import DistributedSetupSecret

from cmk.automations.results import ABCAutomationResult, ResultTypeRegistry, SerializedResult

from cmk.gui.exceptions import MKAuthException
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
            if for_cmk_version >= cmk_version.Version.from_str("2.5.0b1")
            else SerializedResult(repr((self.field_1,)))
        )

    @staticmethod
    def automation_call() -> str:
        return "test"


class TestPageAutomation:
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
    def _check_mk_local_automation_serialized(
        **_kwargs: object,
    ) -> tuple[Sequence[str], str]:
        return (
            ["x", "y", "z"],
            "((1, 2), 'this field was not sent by version N-1')",
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
        monkeypatch.setattr(cmk_version, "edition", lambda *args, **kw: cmk_version.Edition.CEE)

    @pytest.fixture(name="fix_secret_checking")
    def patch_distributed_setup_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            DistributedSetupSecret, "compare", lambda _self, other: other.raw == "secret"
        )

    @pytest.fixture(name="setup_request")
    def setup_request_fixture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        request.set_var("secret", "secret")
        request.set_var("command", "checkmk-automation")
        request.set_var("automation", "test")
        request.set_var("arguments", mk_repr(None).decode())
        request.set_var("indata", mk_repr(None).decode())
        request.set_var("stdin_data", mk_repr(None).decode())
        request.set_var("timeout", mk_repr(None).decode())

    @pytest.mark.usefixtures(
        "request_context",
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "setup_request",
        "patch_edition",
        "fix_secret_checking",
    )
    def test_execute_cmk_automation_current_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with monkeypatch.context() as m:
            m.setattr(
                request,
                "headers",
                {"x-checkmk-version": cmk_version.__version__, "x-checkmk-edition": "cee"},
            )
            automation.PageAutomation()._execute_cmk_automation(debug=False)
            assert response.get_data() == b"((1, 2), 'this field was not sent by version N-1')"

    @pytest.mark.usefixtures(
        "request_context",
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "setup_request",
        "fix_secret_checking",
        "patch_edition",
    )
    def test_execute_cmk_automation_previous_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with monkeypatch.context() as m:
            m.setattr(
                request,
                "headers",
                {"x-checkmk-version": "2.4.0p3", "x-checkmk-edition": "cee"},
            )
            automation.PageAutomation()._execute_cmk_automation(debug=False)
            assert response.get_data() == b"((1, 2),)"

    @pytest.mark.usefixtures(
        "request_context",
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "setup_request",
        "fix_secret_checking",
        "patch_edition",
    )
    def test_execute_cmk_automation_previous_version_incompatible(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with monkeypatch.context() as m:
            m.setattr(
                request,
                "headers",
                {"x-checkmk-version": "2.4.0b1", "x-checkmk-edition": "cee"},
            )
            with pytest.raises(MKGeneralException, match="not compatible"):
                automation.PageAutomation()._execute_cmk_automation(debug=False)

    @pytest.mark.parametrize(
        "incomp_version",
        [
            "1.6.0p23",  # very old major
            "10.0.0",  # newer major
        ],
    )
    @pytest.mark.usefixtures(
        "request_context",
        "result_type_registry",
        "check_mk_local_automation_serialized",
        "setup_request",
        "fix_secret_checking",
        "patch_edition",
    )
    def test_execute_cmk_automation_incompatible(
        self, incomp_version: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with monkeypatch.context() as m:
            m.setattr(
                request,
                "headers",
                {"x-checkmk-version": incomp_version, "x-checkmk-edition": "cee"},
            )
            with pytest.raises(MKGeneralException, match="not compatible"):
                automation.PageAutomation()._execute_cmk_automation(debug=False)

    @pytest.mark.usefixtures(
        "request_context",
        "patch_edition",
    )
    def test_no_secret(self) -> None:
        with pytest.raises(MKAuthException):
            automation.PageAutomation._authenticate()

    @pytest.mark.usefixtures(
        "request_context",
        "patch_edition",
        "fix_secret_checking",
    )
    def test_wrong_secret(self) -> None:
        request.set_var("secret", "wrong")
        with pytest.raises(MKAuthException):
            automation.PageAutomation._authenticate()

    @pytest.mark.usefixtures(
        "request_context",
        "patch_edition",
        "fix_secret_checking",
    )
    def test_correct_secret(self) -> None:
        request.set_var("secret", "secret")
        automation.PageAutomation._authenticate()


def test_automation_login(with_admin: tuple[UserId, str], flask_app: Flask) -> None:
    (paths.var_dir / "wato/automation_secret.mk").write_text(repr("pssst"))

    with flask_app.app_context():
        client = flask_app.test_client(use_cookies=True)

        origtarget = f"automation_login.py?_version={cmk_version.__version__}&_edition_short={cmk_version.edition(paths.omd_root).short}"
        login_resp = client.post(
            "/NO_SITE/check_mk/login.py",
            data={
                "_username": with_admin[0],
                "_password": with_admin[1],
                "_login": "Login",
                "_origtarget": origtarget,
            },
        )
        assert login_resp.status_code == 302
        assert login_resp.location == origtarget

        resp = client.get(f"/NO_SITE/check_mk/{origtarget}")
        assert resp.status_code == 200
        assert ast.literal_eval(resp.text) == {
            "version": cmk_version.__version__,
            "edition_short": cmk_version.edition(paths.omd_root).short,
            "login_secret": "pssst",
        }
