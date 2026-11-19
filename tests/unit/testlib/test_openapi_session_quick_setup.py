#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Behavioural tests for ``QuickSetupAPI.run_action_and_wait``.

Each test targets one observable outcome (return value, raised exception)
rather than internal implementation details.  HTTP responses and background-job
state are injected via lightweight stubs so that the tests run without a live
Checkmk site.
"""

from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from tests.testlib.system.openapi_session import (
    AuthorizationFailed,
    QuickSetupAlreadyRunning,
    QuickSetupAPI,
    UnexpectedResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: HTTPStatus,
    *,
    json_body: object = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_body
    resp.headers = headers or {}
    return resp


def _job_status_response(state: str) -> dict[str, object]:
    """Return the structure that ``BackgroundJobsAPI.show`` would return."""
    return {"extensions": {"status": {"state": state}}}


def _action_result(
    *,
    exception: dict[str, str] | None = None,
    stage_errors: list[str] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {}
    if exception is not None:
        result["background_job_exception"] = exception
    if stage_errors is not None:
        result["all_stage_errors"] = stage_errors
    return result


def _make_api(
    *,
    post_response: MagicMock,
    get_response: MagicMock | None = None,
    bg_job_states: list[str] | None = None,
) -> tuple[QuickSetupAPI, MagicMock]:
    """Build a ``QuickSetupAPI`` backed by a mock session.

    Returns the API instance and the underlying mock session so tests
    can inspect call counts and arguments without going through typed
    attribute chains that mypy cannot resolve.
    """
    session = MagicMock()
    session.post.return_value = post_response
    if get_response is not None:
        session.get.return_value = get_response
    if bg_job_states is not None:
        session.background_jobs.show.side_effect = [_job_status_response(s) for s in bg_job_states]
    api = QuickSetupAPI.__new__(QuickSetupAPI)
    api.session = session
    return api, session


_REDIRECT_HEADERS = {"Location": "/objects/background_job/my-job-123"}
_QS_ID = "aws"
_PAYLOAD: dict[str, object] = {"stages": []}


# ---------------------------------------------------------------------------
# Immediate responses (no background job)
# ---------------------------------------------------------------------------


class TestImmediateResponses:
    """POST returns a final status immediately — no background job polling."""

    def test_created_returns_json(self) -> None:
        body = {"id": "bundle-1"}
        api, _session = _make_api(post_response=_make_response(HTTPStatus.CREATED, json_body=body))

        result = api.run_action_and_wait(_QS_ID, _PAYLOAD)

        assert result == body

    def test_bad_request_raises_unexpected_response(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.BAD_REQUEST, text="validation error"),
        )

        with pytest.raises(UnexpectedResponse):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)

    def test_forbidden_raises_authorization_failed(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.FORBIDDEN, text="no permission"),
        )

        with pytest.raises(AuthorizationFailed):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)

    def test_not_found_raises_unexpected_response(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.NOT_FOUND, text="nope"),
        )

        with pytest.raises(UnexpectedResponse, match="not found"):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)

    def test_too_many_requests_raises_already_running(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.TOO_MANY_REQUESTS, text="busy"),
        )

        with pytest.raises(QuickSetupAlreadyRunning):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)

    def test_unexpected_status_raises_unexpected_response(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.INTERNAL_SERVER_ERROR, text="boom"),
        )

        with pytest.raises(UnexpectedResponse):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)


# ---------------------------------------------------------------------------
# Background-job path (302 / 303 redirect)
# ---------------------------------------------------------------------------


class TestBackgroundJobSuccess:
    """POST redirects to a background job that completes successfully."""

    @pytest.mark.parametrize(
        "redirect_status",
        [
            pytest.param(HTTPStatus.FOUND, id="302"),
            pytest.param(HTTPStatus.SEE_OTHER, id="303"),
        ],
    )
    def test_finished_job_returns_action_result(self, redirect_status: HTTPStatus) -> None:
        expected = {"config_bundle_id": "bundle-42"}
        api, _session = _make_api(
            post_response=_make_response(redirect_status, headers=_REDIRECT_HEADERS),
            get_response=_make_response(HTTPStatus.OK, json_body=expected),
            bg_job_states=["finished"],
        )

        result = api.run_action_and_wait(_QS_ID, _PAYLOAD)

        assert result == expected

    def test_polls_until_terminal_state(self) -> None:
        api, session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=_REDIRECT_HEADERS),
            get_response=_make_response(HTTPStatus.OK, json_body={}),
            bg_job_states=["running", "running", "finished"],
        )

        api.run_action_and_wait(_QS_ID, _PAYLOAD)

        assert session.background_jobs.show.call_count == 3

    def test_job_id_extracted_from_location_header(self) -> None:
        headers = {"Location": "/api/1.0/objects/background_job/special-job-99"}
        api, session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=headers),
            get_response=_make_response(HTTPStatus.OK, json_body={}),
            bg_job_states=["finished"],
        )

        api.run_action_and_wait(_QS_ID, _PAYLOAD)

        session.background_jobs.show.assert_called_with("special-job-99")

    def test_trailing_slash_stripped_from_location(self) -> None:
        headers = {"Location": "/objects/background_job/job-with-slash/"}
        api, session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=headers),
            get_response=_make_response(HTTPStatus.OK, json_body={}),
            bg_job_states=["finished"],
        )

        api.run_action_and_wait(_QS_ID, _PAYLOAD)

        session.background_jobs.show.assert_called_with("job-with-slash")


class TestBackgroundJobFailures:
    """Background job ends in a non-success state."""

    def test_exception_state_raises_runtime_error(self) -> None:
        action_result = _action_result(
            exception={"message": "host conflict", "traceback": "Traceback ..."},
        )
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=_REDIRECT_HEADERS),
            get_response=_make_response(HTTPStatus.OK, json_body=action_result),
            bg_job_states=["exception"],
        )

        with pytest.raises(RuntimeError, match="host conflict"):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)

    def test_stage_errors_raise_runtime_error(self) -> None:
        action_result = _action_result(stage_errors=["field X is required"])
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=_REDIRECT_HEADERS),
            get_response=_make_response(HTTPStatus.OK, json_body=action_result),
            bg_job_states=["finished"],
        )

        with pytest.raises(RuntimeError, match="stage errors"):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)

    def test_stopped_job_raises_runtime_error(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=_REDIRECT_HEADERS),
            bg_job_states=["stopped"],
        )

        with pytest.raises(RuntimeError, match="was stopped"):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)

    def test_timeout_raises_timeout_error(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=_REDIRECT_HEADERS),
            bg_job_states=["running"] * 50,
        )

        with pytest.raises(TimeoutError):
            api.run_action_and_wait(_QS_ID, _PAYLOAD, timeout=0)

    def test_action_result_fetch_failure_raises(self) -> None:
        api, _session = _make_api(
            post_response=_make_response(HTTPStatus.FOUND, headers=_REDIRECT_HEADERS),
            get_response=_make_response(HTTPStatus.INTERNAL_SERVER_ERROR, text="db down"),
            bg_job_states=["finished"],
        )

        with pytest.raises(UnexpectedResponse):
            api.run_action_and_wait(_QS_ID, _PAYLOAD)
