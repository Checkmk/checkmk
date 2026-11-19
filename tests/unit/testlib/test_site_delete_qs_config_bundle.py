#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Behaviour tests for the quick-setup bundle deletion helper.

Each test targets one observable outcome (exit code, stderr output)
rather than internal implementation details.
"""

import subprocess
from collections.abc import Callable

import pytest

from tests.testlib.system import site as site_module
from tests.testlib.system._helper_delete_qs_config_bundle import delete_bundle
from tests.testlib.system.site import Site


def _noop(_bid: str) -> None:
    pass


def _raise_runtime_error(_bid: str) -> None:
    raise RuntimeError("ERROR")


class TestDeleteBundle:
    """Behavioural tests for `delete_bundle`."""

    @pytest.mark.parametrize(
        "bundle_id, bundle_exists, delete_fn, expected_exit_code",
        [
            pytest.param("no-such-bundle", lambda _bid: False, _noop, 1, id="absent_bundle"),
            pytest.param("my-bundle", lambda _bid: True, _noop, 0, id="successful_deletion"),
            pytest.param(
                "broken-bundle",
                lambda _bid: True,
                _raise_runtime_error,
                2,
                id="deletion_error",
            ),
        ],
    )
    def test_exit_code(
        self,
        bundle_id: str,
        bundle_exists: Callable[[str], bool],
        delete_fn: Callable[[str], None],
        expected_exit_code: int,
    ) -> None:
        exit_code = delete_bundle(bundle_id, bundle_exists=bundle_exists, delete=delete_fn)

        assert exit_code == expected_exit_code

    def test_deletion_error_writes_details_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        delete_bundle(
            "broken-bundle",
            bundle_exists=lambda _bid: True,
            delete=_raise_runtime_error,
        )

        stderr = capsys.readouterr().err
        assert "broken-bundle" in stderr
        assert "RuntimeError" in stderr
        assert "ERROR" in stderr

    def test_delete_not_called_when_bundle_absent(self) -> None:
        called = False

        def _must_not_be_called(_bid: str) -> None:
            nonlocal called
            called = True

        delete_bundle(
            "ghost",
            bundle_exists=lambda _bid: False,
            delete=_must_not_be_called,
        )

        assert not called


def _completed(returncode: int, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["python3"], returncode=returncode, stdout="", stderr=stderr
    )


@pytest.fixture(name="site")
def fixture_site() -> Site:
    return object.__new__(Site)


class _PythonHelperStub:
    """Stand-in for `PythonHelper` that returns a canned `CompletedProcess`."""

    def __init__(self, result: subprocess.CompletedProcess[str]) -> None:
        self._result = result

    def __call__(self, _site: Site, _helper_path: object) -> _PythonHelperStub:
        return self

    def run(self, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return self._result


class TestDeleteQsConfigBundle:
    """Behavioural tests for `Site.delete_qs_config_bundle`."""

    @pytest.mark.parametrize(
        "returncode",
        [
            pytest.param(0, id="deleted"),
            pytest.param(1, id="absent"),
        ],
    )
    def test_acceptable_exit_codes_return_result(
        self,
        site: Site,
        monkeypatch: pytest.MonkeyPatch,
        returncode: int,
    ) -> None:
        monkeypatch.setattr(site_module, "PythonHelper", _PythonHelperStub(_completed(returncode)))

        result = site.delete_qs_config_bundle("some-bundle")

        assert result.returncode == returncode

    def test_unexpected_exit_code_raises_with_stderr(
        self, site: Site, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            site_module,
            "PythonHelper",
            _PythonHelperStub(_completed(2, stderr="traceback here")),
        )

        with pytest.raises(RuntimeError, match="traceback here"):
            site.delete_qs_config_bundle("broken-bundle")
