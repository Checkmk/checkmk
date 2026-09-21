#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import logging.handlers
import queue
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.web.context import RequestProtocol
from cmk.web.utils.csrf_token import check_csrf_token

TOKEN = "3a1f0f1e-0c4a-4b3a-9f0e-0d1c2b3a4f5e"


@dataclass(frozen=True)
class FakeSessionUser:
    id: UserId | None
    is_anonymous: bool


@dataclass(frozen=True)
class FakeSessionInfo:
    csrf_token: str


@dataclass(frozen=True)
class FakeSession:
    user: FakeSessionUser
    session_info: FakeSessionInfo


def logged_in_session() -> FakeSession:
    return FakeSession(
        user=FakeSessionUser(id=UserId("harri"), is_anonymous=False),
        session_info=FakeSessionInfo(csrf_token=TOKEN),
    )


def anonymous_session() -> FakeSession:
    return FakeSession(
        user=FakeSessionUser(id=None, is_anonymous=True),
        session_info=FakeSessionInfo(csrf_token=TOKEN),
    )


def request_with(
    *,
    variables: Mapping[str, str] | None = None,
    body: Mapping[str, object] | None = None,
) -> Mock:
    """A request that answers from the given variables and body, nothing else."""
    request = Mock(spec=RequestProtocol)
    request.get_str_input.side_effect = lambda varname, deflt=None: (variables or {}).get(
        varname, deflt
    )
    request.get_request.return_value = body or {}
    request.remote_ip = "192.0.2.10"
    return request


def identity(text: str) -> str:
    return text


@pytest.fixture(name="security_log")
def fixture_security_log() -> Iterator[queue.Queue[logging.LogRecord]]:
    """Keep the security logger from opening its log file, and record what it gets."""
    records: queue.Queue[logging.LogRecord] = queue.Queue()
    handler = logging.handlers.QueueHandler(records)

    logger = logging.getLogger("cmk_security")
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        yield records
    finally:
        logger.setLevel(previous_level)
        logger.removeHandler(handler)


def test_an_anonymous_session_needs_no_token() -> None:
    check_csrf_token(anonymous_session(), request_with(), i18n=identity)


def test_the_token_is_taken_from_the_request_variable() -> None:
    check_csrf_token(
        logged_in_session(), request_with(variables={"_csrf_token": TOKEN}), i18n=identity
    )


def test_the_token_is_taken_from_the_request_body() -> None:
    check_csrf_token(logged_in_session(), request_with(body={"_csrf_token": TOKEN}), i18n=identity)


def test_the_token_given_by_the_caller_wins_over_the_request() -> None:
    check_csrf_token(
        logged_in_session(),
        request_with(variables={"_csrf_token": "some other token"}),
        i18n=identity,
        token=TOKEN,
    )


@pytest.mark.usefixtures("security_log")
def test_a_request_without_a_token_is_rejected() -> None:
    with pytest.raises(MKGeneralException, match="No CSRF token received"):
        check_csrf_token(logged_in_session(), request_with(), i18n=identity)


@pytest.mark.usefixtures("security_log")
def test_a_request_with_another_sessions_token_is_rejected() -> None:
    with pytest.raises(MKGeneralException, match="Invalid CSRF token"):
        check_csrf_token(
            logged_in_session(),
            request_with(variables={"_csrf_token": "token of another session"}),
            i18n=identity,
        )


@pytest.mark.usefixtures("security_log")
def test_the_rejection_message_is_translated_by_the_caller() -> None:
    with pytest.raises(MKGeneralException, match="übersetzt: No CSRF token received"):
        check_csrf_token(
            logged_in_session(), request_with(), i18n=lambda text: f"übersetzt: {text}"
        )


def test_a_rejected_request_is_logged_as_a_security_event(
    security_log: queue.Queue[logging.LogRecord],
) -> None:
    with pytest.raises(MKGeneralException):
        check_csrf_token(logged_in_session(), request_with(), i18n=identity)

    record = security_log.get_nowait()
    assert record.name == "cmk_security.application_errors"
    assert json.loads(record.getMessage()) == {
        "summary": "CSRF token missing",
        "details": {"user": "harri", "remote_ip": "192.0.2.10"},
    }
