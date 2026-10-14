#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from tests.testlib.system.mock_server import (
    MockEndpoint,
    MockEndpoints,
    MockMethod,
    MockResponse,
    ReceivedRequest,
)

_VERIFY = MockEndpoint(method=MockMethod.POST, path="/verify")


def _post(path: str, body: bytes = b"") -> ReceivedRequest:
    return ReceivedRequest(method=MockMethod.POST, path=path, headers={}, body=body)


def test_mock_answers_with_the_configured_response() -> None:
    endpoints = MockEndpoints()
    endpoints.add(_VERIFY, MockResponse(status=HTTPStatus.CREATED, body=b'{"status": "ok"}'))

    answer = endpoints.answer(_post("/verify"))

    assert (answer.status, answer.body) == (HTTPStatus.CREATED, b'{"status": "ok"}')


def test_mock_builds_the_answer_body_from_the_request() -> None:
    endpoints = MockEndpoints()
    endpoints.add(
        _VERIFY, MockResponse(status=HTTPStatus.OK, body=lambda _headers, body: body.upper())
    )

    answer = endpoints.answer(_post("/verify", b"abc"))

    assert answer.body == b"ABC"


def test_mock_answers_an_unknown_path_with_not_found() -> None:
    endpoints = MockEndpoints()
    endpoints.add(_VERIFY, MockResponse(status=HTTPStatus.OK, body=b"{}"))

    answer = endpoints.answer(_post("/unknown"))

    assert answer.status == HTTPStatus.NOT_FOUND


def test_mock_rejects_a_request_its_validator_refuses() -> None:
    endpoints = MockEndpoints()
    endpoints.add(
        _VERIFY,
        MockResponse(
            status=HTTPStatus.OK, body=b"{}", request_validator=lambda _headers, _body: False
        ),
    )

    answer = endpoints.answer(_post("/verify"))

    assert answer.status == HTTPStatus.BAD_REQUEST
