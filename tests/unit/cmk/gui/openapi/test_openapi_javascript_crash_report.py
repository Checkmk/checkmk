#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import shutil
from collections.abc import Mapping

import pytest

import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.crash import make_crash_report_base_path
from tests.testlib.rest_api_client import ClientRegistry

_STACK = "TypeError: boom\n    at renderTile (http://localhost/NO_SITE/check_mk/js/main.js:120:31)"

_BODY = {
    "error_name": "TypeError",
    "error_message": "Cannot read properties of undefined (reading 'title')",
    "url": "http://localhost/NO_SITE/check_mk/dashboard.py",
    "stack": _STACK,
    "component": "DashboardApp",
    "context": "GET http://localhost/NO_SITE/check_mk/api/internal/version\nSTATUS 500",
}


def _pop_stored_crash_infos() -> list[Mapping[str, object]]:
    """Read the stored javascript crashes and delete them.

    The test session fails on any crash report left behind, so a test producing one
    on purpose has to consume it.
    """
    base_path = make_crash_report_base_path(cmk.utils.paths.omd_root) / "javascript"
    crash_infos = [json.loads(path.read_text()) for path in sorted(base_path.glob("*/crash.info"))]
    shutil.rmtree(base_path, ignore_errors=True)
    return crash_infos


def _nested(crash_info: Mapping[str, object], key: str) -> Mapping[str, object]:
    nested = crash_info[key]
    assert isinstance(nested, dict)
    return nested


def test_create_javascript_crash_report(clients: ClientRegistry) -> None:
    response = clients.JavascriptCrashReport.create(_BODY)
    _pop_stored_crash_infos()

    assert response.status_code == 201
    assert response.json["domainType"] == "javascript_crash_report"
    assert response.json["extensions"]["crash_type"] == "javascript"
    assert response.json["extensions"]["crash_report_url"] == (
        f"crash.py?crash_id={response.json['id']}&site=NO_SITE"
    )


def test_create_javascript_crash_report_stores_the_reported_error(
    clients: ClientRegistry,
) -> None:
    clients.JavascriptCrashReport.create(_BODY)

    (crash_info,) = _pop_stored_crash_infos()
    assert crash_info["crash_type"] == "javascript"
    assert crash_info["exc_type"] == "TypeError"
    assert crash_info["exc_value"] == "Cannot read properties of undefined (reading 'title')"
    assert crash_info["exc_traceback"] == [
        [
            "http://localhost/NO_SITE/check_mk/js/main.js",
            120,
            "renderTile",
            "at renderTile (http://localhost/NO_SITE/check_mk/js/main.js:120:31)",
        ]
    ]
    details = _nested(crash_info, "details")
    assert details["url"] == _BODY["url"]
    assert details["component"] == "DashboardApp"
    assert details["context"] == _BODY["context"]


def test_create_javascript_crash_report_records_the_reporting_user(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    clients.JavascriptCrashReport.create(_BODY)

    (crash_info,) = _pop_stored_crash_infos()
    assert _nested(crash_info, "details")["username"] == with_automation_user[0]


def test_create_javascript_crash_report_deduplicates_repeated_errors(
    clients: ClientRegistry,
) -> None:
    clients.JavascriptCrashReport.create(_BODY)
    clients.JavascriptCrashReport.create(_BODY)

    (crash_info,) = _pop_stored_crash_infos()
    assert _nested(crash_info, "occurrences")["count"] == 2


def test_create_javascript_crash_report_never_stores_python_local_variables(
    clients: ClientRegistry,
) -> None:
    clients.JavascriptCrashReport.create(_BODY)

    (crash_info,) = _pop_stored_crash_infos()
    assert crash_info["local_vars"] == ""


@pytest.mark.parametrize(
    "missing_field",
    [
        pytest.param("error_name", id="error-name-is-required"),
        pytest.param("error_message", id="error-message-is-required"),
        pytest.param("url", id="url-is-required"),
    ],
)
def test_create_javascript_crash_report_requires_the_error_identity(
    clients: ClientRegistry, missing_field: str
) -> None:
    body = {key: value for key, value in _BODY.items() if key != missing_field}

    response = clients.JavascriptCrashReport.create(body, expect_ok=False)

    assert response.status_code == 400
    assert _pop_stored_crash_infos() == []


@pytest.mark.parametrize(
    "field, max_length",
    [
        pytest.param("error_name", 1024, id="error-name"),
        pytest.param("component", 1024, id="component"),
        pytest.param("url", 8192, id="url"),
        pytest.param("error_message", 64 * 1024, id="error-message"),
        pytest.param("stack", 64 * 1024, id="stack"),
        pytest.param("context", 64 * 1024, id="context"),
    ],
)
def test_create_javascript_crash_report_field_length_limits(
    clients: ClientRegistry, field: str, max_length: int
) -> None:
    accepted = clients.JavascriptCrashReport.create({**_BODY, field: "a" * max_length})
    assert accepted.status_code == 201
    assert len(_pop_stored_crash_infos()) == 1

    rejected = clients.JavascriptCrashReport.create(
        {**_BODY, field: "a" * (max_length + 1)}, expect_ok=False
    )
    assert rejected.status_code == 400
    assert _pop_stored_crash_infos() == []
