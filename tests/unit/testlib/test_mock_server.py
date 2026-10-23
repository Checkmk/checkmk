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


def test_mock_answers_with_the_responses_in_turn_and_repeats_the_last() -> None:
    endpoints = MockEndpoints()
    endpoints.add(
        _VERIFY,
        MockResponse(status=HTTPStatus.SERVICE_UNAVAILABLE, body=b"{}"),
        MockResponse(status=HTTPStatus.OK, body=b"{}"),
    )

    statuses = [endpoints.answer(_post("/verify")).status for _ in range(3)]

    assert statuses == [HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.OK, HTTPStatus.OK]


def test_mock_records_every_request_in_order() -> None:
    endpoints = MockEndpoints()
    endpoints.add(_VERIFY, MockResponse(status=HTTPStatus.OK, body=b"{}"))
    known = _post("/verify", b'{"email": "team-ghost@checkmk.com"}')
    unknown = _post("/unknown")

    endpoints.answer(known)
    endpoints.answer(unknown)

    assert endpoints.received_requests == [known, unknown]


def test_mock_reset_forgets_endpoints_and_requests() -> None:
    endpoints = MockEndpoints()
    endpoints.add(_VERIFY, MockResponse(status=HTTPStatus.OK, body=b"{}"))
    endpoints.answer(_post("/verify"))

    endpoints.reset()
    answer = endpoints.answer(_post("/verify"))

    assert answer.status == HTTPStatus.NOT_FOUND
    assert endpoints.received_requests == [_post("/verify")]
