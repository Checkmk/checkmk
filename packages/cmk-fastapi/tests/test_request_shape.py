#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass, field
from http import HTTPStatus

import pytest
from starlette.types import Message, Receive, Scope, Send

from cmk.fastapi.request_shape import (
    CROSS_ORIGIN_DETAIL,
    NOT_JSON_DETAIL,
    RequestShapeMiddleware,
)

BODY = (b"content-length", b"13")


@dataclass
class RecordingApp:
    scopes: list[Scope] = field(default_factory=list)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,  # noqa: ARG002
        send: Send,
    ) -> None:
        self.scopes.append(scope)
        if scope["type"] == "http":
            await send({"type": "http.response.start", "status": HTTPStatus.OK, "headers": []})
            await send({"type": "http.response.body", "body": b""})


@dataclass(frozen=True)
class Outcome:
    status: int
    detail: str | None
    reached_app: bool
    body_read: bool


async def call(headers: list[tuple[bytes, bytes]]) -> Outcome:
    app = RecordingApp()
    sent: list[Message] = []
    receive_calls = 0

    async def receive() -> Message:
        nonlocal receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": b'{"text":"hi"}', "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {"type": "http", "method": "POST", "path": "/", "headers": headers}
    await RequestShapeMiddleware(app)(scope, receive, send)

    body = sent[1]["body"]
    return Outcome(
        status=sent[0]["status"],
        detail=json.loads(body)["detail"] if body else None,
        reached_app=bool(app.scopes),
        body_read=receive_calls > 0,
    )


@pytest.mark.parametrize(
    "sec_fetch_site",
    [
        pytest.param([b"cross-site"], id="cross-site"),
        pytest.param([b"same-site"], id="same-site"),
        pytest.param([b"none"], id="none"),
        pytest.param([b""], id="empty"),
        pytest.param([b"Same-Origin"], id="other-case"),
        pytest.param([b"same-origin", b"cross-site"], id="repeated"),
    ],
)
@pytest.mark.asyncio
async def test_sec_fetch_site_other_than_same_origin_is_refused_before_the_app(
    sec_fetch_site: list[bytes],
) -> None:
    headers = [(b"sec-fetch-site", value) for value in sec_fetch_site]

    assert await call(headers) == Outcome(
        status=HTTPStatus.FORBIDDEN, detail=CROSS_ORIGIN_DETAIL, reached_app=False, body_read=False
    )


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param([], id="missing"),
        pytest.param([(b"sec-fetch-site", b"same-origin")], id="same-origin"),
    ],
)
@pytest.mark.asyncio
async def test_same_origin_or_missing_sec_fetch_site_reaches_the_app(
    headers: list[tuple[bytes, bytes]],
) -> None:
    assert (await call(headers)).reached_app


@pytest.mark.parametrize(
    "content_type",
    [
        pytest.param([b"text/plain"], id="text-plain"),
        pytest.param([b"application/x-www-form-urlencoded"], id="form"),
        pytest.param([b"multipart/form-data; boundary=x"], id="multipart"),
        pytest.param([b"application/problem+json"], id="json-suffix"),
        pytest.param([b"application/jsonx"], id="json-prefix"),
        pytest.param([], id="missing"),
        pytest.param([b"application/json", b"text/plain"], id="repeated"),
    ],
)
@pytest.mark.parametrize(
    "framing",
    [
        pytest.param((b"content-length", b"13"), id="content-length"),
        pytest.param((b"transfer-encoding", b"chunked"), id="chunked"),
    ],
)
@pytest.mark.asyncio
async def test_body_without_json_media_type_is_refused_without_reading_it(
    content_type: list[bytes], framing: tuple[bytes, bytes]
) -> None:
    headers = [framing, *((b"content-type", value) for value in content_type)]

    assert await call(headers) == Outcome(
        status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        detail=NOT_JSON_DETAIL,
        reached_app=False,
        body_read=False,
    )


@pytest.mark.parametrize(
    "content_length",
    [
        pytest.param([b"abc"], id="not-a-number"),
        pytest.param([b"-1"], id="negative"),
        pytest.param([b""], id="empty"),
        pytest.param([b"0", b"13"], id="repeated"),
    ],
)
@pytest.mark.asyncio
async def test_unparsable_content_length_counts_as_a_body(content_length: list[bytes]) -> None:
    headers = [
        *((b"content-length", value) for value in content_length),
        (b"content-type", b"text/plain"),
    ]

    assert (await call(headers)).status == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


@pytest.mark.parametrize(
    "content_type",
    [
        pytest.param(b"application/json", id="plain"),
        pytest.param(b"application/json; charset=utf-8", id="with-charset"),
        pytest.param(b"Application/JSON", id="other-case"),
    ],
)
@pytest.mark.asyncio
async def test_body_with_json_media_type_reaches_the_app(content_type: bytes) -> None:
    assert (await call([BODY, (b"content-type", content_type)])).reached_app


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param([], id="no-framing-headers"),
        pytest.param([(b"content-length", b"0")], id="content-length-0"),
        pytest.param(
            [(b"content-length", b"0"), (b"content-type", b"text/plain")],
            id="content-length-0-wrong-media-type",
        ),
    ],
)
@pytest.mark.asyncio
async def test_request_without_body_skips_the_media_type_check(
    headers: list[tuple[bytes, bytes]],
) -> None:
    assert (await call(headers)).reached_app


@pytest.mark.asyncio
async def test_cross_site_request_with_a_wrong_body_is_refused_as_cross_site() -> None:
    headers = [(b"sec-fetch-site", b"cross-site"), BODY, (b"content-type", b"text/plain")]

    assert (await call(headers)).status == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_non_http_scope_is_passed_through() -> None:
    app = RecordingApp()
    scope: Scope = {"type": "lifespan"}

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        pass

    await RequestShapeMiddleware(app)(scope, receive, send)

    assert app.scopes == [scope]


@pytest.mark.asyncio
async def test_an_exempt_path_reaches_the_app_from_another_site() -> None:
    app = RecordingApp()

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message: Message) -> None:
        pass

    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/healthz",
        "headers": [(b"sec-fetch-site", b"cross-site")],
    }
    await RequestShapeMiddleware(app, exempt_paths=frozenset({"/healthz"}))(scope, receive, send)

    assert app.scopes == [scope]
