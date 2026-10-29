#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import json
import logging
from http import HTTPStatus
from pathlib import Path

import httpx2
import pytest

from cmk.fastapi.gui_session import (
    GuiLoopback,
    Identity,
    loopback_http_client,
    Rejected,
    Unavailable,
)

_COOKIE = "jdoe:4f1c2b1e-0d7a-4a3b-9a55-8d9d7c3a2b10:9c1e0000"


type _Answer = httpx2.Response | Exception


class _GUI:
    """Answers every request with the same answer, and keeps the requests."""

    def __init__(self, answer: _Answer) -> None:
        self.answer = answer
        self.requests: list[httpx2.Request] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def _identified() -> httpx2.Response:
    return httpx2.Response(
        HTTPStatus.OK, json={"user_id": "jdoe", "permissions": {"maps.use": True}}
    )


def _problem(status: int, **ext: str) -> httpx2.Response:
    body: dict[str, object] = {"title": "t", "status": status, "detail": "d"}
    if ext:
        body["ext"] = ext
    return httpx2.Response(status, json=body)


@pytest.fixture(name="omd_root")
def fixture_omd_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("OMD_SITE", "mysite")
    (tmp_path / "etc/omd").mkdir(parents=True)
    (tmp_path / "etc/omd/site.conf").write_text("CONFIG_APACHE_TCP_PORT='5000'\n")
    (tmp_path / "etc/site_internal.secret").write_bytes(b"the secret")
    return tmp_path


def _loopback(gui: _GUI, omd_root: Path) -> GuiLoopback:
    return GuiLoopback(loopback_http_client(omd_root, transport=httpx2.MockTransport(gui.handle)))


def _secret_file(omd_root: Path) -> Path:
    return omd_root / "etc/site_internal.secret"


def _authorization(secret: bytes) -> str:
    return f"InternalToken {base64.b64encode(secret).decode()}"


@pytest.mark.asyncio
async def test_identify_asks_this_site_with_the_site_secret_for_what_the_caller_needs(
    omd_root: Path,
) -> None:
    gui = _GUI(httpx2.Response(HTTPStatus.OK, json={"user_id": "jdoe"}))

    await _loopback(gui, omd_root).identify(
        _COOKIE, required_permissions=["maps.use"], include_contact_groups=True
    )

    assert [
        (str(r.url), r.headers["Authorization"], json.loads(r.content)) for r in gui.requests
    ] == [
        (
            "http://localhost:5000/mysite/check_mk/api/internal/domain-types/gui_session/actions/identify/invoke",
            _authorization(b"the secret"),
            {
                "session_cookie": _COOKIE,
                "required_permissions": ["maps.use"],
                "include_contact_groups": True,
            },
        )
    ]


@pytest.mark.asyncio
async def test_identify_asks_only_for_the_user_by_default(omd_root: Path) -> None:
    gui = _GUI(httpx2.Response(HTTPStatus.OK, json={"user_id": "jdoe"}))

    result = await _loopback(gui, omd_root).identify(_COOKIE)

    assert [json.loads(r.content) for r in gui.requests] == [{"session_cookie": _COOKIE}]
    assert result == Identity(user_id="jdoe", permissions={}, contact_groups=[])


@pytest.mark.asyncio
async def test_identify_answers_the_permissions_and_contact_groups(omd_root: Path) -> None:
    gui = _GUI(
        httpx2.Response(
            HTTPStatus.OK,
            json={
                "user_id": "jdoe",
                "permissions": {"maps.use": True},
                "contact_groups": ["linux"],
            },
        )
    )

    result = await _loopback(gui, omd_root).identify(
        _COOKIE, required_permissions=["maps.use"], include_contact_groups=True
    )

    assert result == Identity(
        user_id="jdoe", permissions={"maps.use": True}, contact_groups=["linux"]
    )


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param({"user_id": "jdoe", "contact_groups": []}, id="permission missing"),
        pytest.param({"user_id": "jdoe", "permissions": {"maps.use": True}}, id="groups missing"),
    ],
)
@pytest.mark.asyncio
async def test_identify_has_no_verdict_without_what_was_asked_for(
    omd_root: Path, answer: dict[str, object]
) -> None:
    gui = _GUI(httpx2.Response(HTTPStatus.OK, json=answer))

    result = await _loopback(gui, omd_root).identify(
        _COOKIE, required_permissions=["maps.use"], include_contact_groups=True
    )

    assert isinstance(result, Unavailable)


@pytest.mark.asyncio
async def test_identify_tells_a_refused_session_apart(omd_root: Path) -> None:
    gui = _GUI(
        httpx2.Response(
            HTTPStatus.BAD_REQUEST,
            json={"title": "t", "status": 400, "detail": "d", "ext": {"error": "invalid_grant"}},
        )
    )

    assert await _loopback(gui, omd_root).identify(_COOKIE) == Rejected()


@pytest.mark.asyncio
async def test_every_call_sends_the_site_secret_that_is_on_disk_right_then(
    omd_root: Path,
) -> None:
    gui = _GUI(_identified())
    loopback = _loopback(gui, omd_root)

    await loopback.identify(_COOKIE)
    _secret_file(omd_root).write_bytes(b"second secret")
    await loopback.identify(_COOKIE)

    assert [r.headers["Authorization"] for r in gui.requests] == [
        _authorization(b"the secret"),
        _authorization(b"second secret"),
    ]


@pytest.mark.asyncio
async def test_without_a_secret_file_nothing_is_sent_and_there_is_no_verdict(
    omd_root: Path,
) -> None:
    _secret_file(omd_root).unlink()
    gui = _GUI(_identified())

    result = await _loopback(gui, omd_root).identify(_COOKIE)

    assert isinstance(result, Unavailable)
    assert gui.requests == []


@pytest.mark.asyncio
async def test_with_an_empty_secret_file_nothing_is_sent_and_there_is_no_verdict(
    omd_root: Path,
) -> None:
    """omd empties the file for a moment each time it writes a new secret"""
    _secret_file(omd_root).write_bytes(b"")
    gui = _GUI(_identified())

    result = await _loopback(gui, omd_root).identify(_COOKIE)

    assert isinstance(result, Unavailable)
    assert gui.requests == []


@pytest.mark.asyncio
async def test_a_missing_site_secret_is_not_created(omd_root: Path) -> None:
    _secret_file(omd_root).unlink()

    await _loopback(_GUI(_identified()), omd_root).identify(_COOKIE)

    assert not _secret_file(omd_root).exists()


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(_problem(HTTPStatus.BAD_REQUEST), id="bad request without an error code"),
        pytest.param(_problem(HTTPStatus.UNAUTHORIZED), id="site secret refused"),
        pytest.param(_problem(HTTPStatus.NOT_FOUND), id="endpoint missing or switched off"),
        pytest.param(_problem(HTTPStatus.INTERNAL_SERVER_ERROR), id="server error"),
        pytest.param(httpx2.Response(HTTPStatus.OK, content=b"<html>"), id="200 that is not JSON"),
        pytest.param(
            httpx2.Response(
                HTTPStatus.OK, json={"user_id": "jdoe", "permissions": {"maps.use": "yes"}}
            ),
            id="200 with a permission that is not a boolean",
        ),
        pytest.param(httpx2.ConnectError("refused"), id="connection refused"),
        pytest.param(httpx2.ReadTimeout("slow"), id="timeout"),
        pytest.param(httpx2.DecodingError("incorrect header check"), id="answer not decodable"),
    ],
)
@pytest.mark.asyncio
async def test_identify_has_no_verdict_for_anything_else(omd_root: Path, answer: _Answer) -> None:
    result = await _loopback(_GUI(answer), omd_root).identify(
        _COOKIE, required_permissions=["maps.use"]
    )

    assert isinstance(result, Unavailable)


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(_problem(HTTPStatus.INTERNAL_SERVER_ERROR), id="server error"),
        pytest.param(httpx2.ConnectError("refused"), id="connection refused"),
    ],
)
@pytest.mark.asyncio
async def test_a_failed_call_is_not_repeated(omd_root: Path, answer: _Answer) -> None:
    gui = _GUI(answer)

    await _loopback(gui, omd_root).identify(_COOKIE)

    assert len(gui.requests) == 1


@pytest.mark.parametrize(
    "answer, logged",
    [
        pytest.param(
            httpx2.Response(
                HTTPStatus.BAD_REQUEST,
                json={
                    "title": "t",
                    "status": 400,
                    "detail": f"about {_COOKIE}",
                    "ext": {"error": "odd"},
                },
            ),
            "The GUI gave no verdict on identify: status 400, error odd",
            id="problem",
        ),
        pytest.param(
            httpx2.Response(HTTPStatus.OK, content=f"<html>{_COOKIE}</html>".encode()),
            "The GUI gave no verdict on identify: status 200, the answer does not have the expected shape",
            id="200 that is not JSON",
        ),
    ],
)
@pytest.mark.asyncio
async def test_the_log_of_an_answer_without_a_verdict_names_the_reason_but_not_the_answer(
    omd_root: Path, caplog: pytest.LogCaptureFixture, answer: httpx2.Response, logged: str
) -> None:
    with caplog.at_level(logging.WARNING):
        await _loopback(_GUI(answer), omd_root).identify(_COOKIE)

    assert [r.getMessage() for r in caplog.records] == [logged]
