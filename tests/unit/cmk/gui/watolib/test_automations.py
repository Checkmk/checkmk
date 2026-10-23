#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

import pytest

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.watolib.automations import get_url_raw

_CENTRAL_BASE = cmk_version.Version.from_str(cmk_version.__version__).base
assert _CENTRAL_BASE is not None
_MAJOR = _CENTRAL_BASE.major


class _FakeResponse:
    def __init__(self, headers: dict[str, str]) -> None:
        self.status_code = HTTPStatus.OK
        self.headers = headers
        self.text = "ok"
        self.encoding = ""


def _serve(monkeypatch: pytest.MonkeyPatch, headers: dict[str, str]) -> None:
    def post(*_args: object, **_kwargs: object) -> _FakeResponse:
        return _FakeResponse(headers)

    monkeypatch.setattr("requests.post", post)


@pytest.mark.parametrize(
    "remote_version",
    [
        pytest.param(f"{_MAJOR - 1}.0.0", id="older major"),
        pytest.param(f"{_MAJOR - 1}.0.0p99", id="older major with higher patch"),
    ],
)
def test_remote_on_older_major_is_refused(
    monkeypatch: pytest.MonkeyPatch, remote_version: str
) -> None:
    _serve(monkeypatch, {"x-checkmk-version": remote_version})

    with pytest.raises(MKGeneralException, match="is newer than the site it contacted"):
        get_url_raw("https://remote/automation.py", insecure=False)


def test_remote_not_allowed_by_licensing_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(
        monkeypatch,
        {"x-checkmk-version": cmk_version.__version__, "x-checkmk-edition": "cloud"},
    )

    with pytest.raises(MKGeneralException, match="Checkmk Cloud is not allowed"):
        get_url_raw("https://remote/automation.py", insecure=False)


@pytest.mark.parametrize(
    "remote_version",
    [
        pytest.param(f"{_CENTRAL_BASE}p1", id="same major"),
        pytest.param(f"{_MAJOR + 1}.0.0", id="one major ahead"),
        pytest.param(f"{_MAJOR + 5}.0.0", id="many majors ahead"),
        pytest.param("2021.12.13", id="old style nightly"),
    ],
)
def test_remote_not_older_than_central_is_accepted(
    monkeypatch: pytest.MonkeyPatch, remote_version: str
) -> None:
    _serve(monkeypatch, {"x-checkmk-version": remote_version})

    response = get_url_raw("https://remote/automation.py", insecure=False)

    assert response.text == "ok"


def test_remote_without_version_header_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, {})

    response = get_url_raw("https://remote/automation.py", insecure=False)

    assert response.text == "ok"
