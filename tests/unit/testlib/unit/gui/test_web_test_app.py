#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from http import HTTPStatus

import flask
import pytest

from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK


def _client_for_app_writing_to_wsgi_errors() -> WebTestAppForCMK:
    app = flask.Flask(__name__)

    @app.get("/")
    def _index() -> str:
        flask.request.environ["wsgi.errors"].write("something went wrong\n")
        return "ok"

    return WebTestAppForCMK(app)


def _client_for_app_raising_after_writing_to_wsgi_errors() -> WebTestAppForCMK:
    app = flask.Flask(__name__)
    app.testing = True

    @app.get("/")
    def _index() -> str:
        flask.request.environ["wsgi.errors"].write("something went wrong\n")
        raise ValueError("boom")

    return WebTestAppForCMK(app)


def _client_for_app_writing_to_wsgi_errors_while_streaming() -> WebTestAppForCMK:
    app = flask.Flask(__name__)

    @app.get("/")
    def _index() -> flask.Response:
        errors = flask.request.environ["wsgi.errors"]

        def body() -> Iterator[str]:
            yield "ok"
            errors.write("something went wrong\n")

        return flask.Response(body())

    return WebTestAppForCMK(app)


def test_request_writing_to_wsgi_errors_fails() -> None:
    client = _client_for_app_writing_to_wsgi_errors()

    with pytest.raises(AssertionError, match="something went wrong"):
        client.get("/")


def test_request_writing_to_wsgi_errors_while_streaming_the_response_fails() -> None:
    client = _client_for_app_writing_to_wsgi_errors_while_streaming()

    with pytest.raises(AssertionError, match="something went wrong"):
        client.get("/")


def test_request_writing_to_wsgi_errors_passes_when_errors_are_expected() -> None:
    client = _client_for_app_writing_to_wsgi_errors()

    resp = client.get("/", expect_errors=True)

    assert resp.status_code == HTTPStatus.OK


def test_wsgi_errors_show_up_on_stderr_when_errors_are_expected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = _client_for_app_writing_to_wsgi_errors()

    client.get("/", expect_errors=True)

    assert capsys.readouterr().err == "something went wrong\n"


def test_wsgi_errors_show_up_on_stderr_when_status_is_unexpected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = _client_for_app_writing_to_wsgi_errors()

    with pytest.raises(AssertionError, match="Expected response code"):
        client.get("/", status=HTTPStatus.CREATED)

    assert capsys.readouterr().err == "something went wrong\n"


def test_wsgi_errors_show_up_on_stderr_when_request_raises(
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = _client_for_app_raising_after_writing_to_wsgi_errors()

    with pytest.raises(ValueError, match="boom"):
        client.get("/")

    assert capsys.readouterr().err == "something went wrong\n"
