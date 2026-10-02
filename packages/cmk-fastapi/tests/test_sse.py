#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import AsyncIterator
from typing import Annotated, Literal, TYPE_CHECKING

import pytest
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from cmk.fastapi import FastAPI
from cmk.fastapi.sse import EventStream, SentEvent

if TYPE_CHECKING:
    from typing_extensions import TypeForm


class Greeting(BaseModel):
    kind: Literal["greeting"] = "greeting"
    text: str


class Reading(BaseModel):
    kind: Literal["reading"] = "reading"
    value: float


class Unrelated(BaseModel):
    kind: Literal["unrelated"] = "unrelated"


Messages = Annotated[Greeting | Reading, Field(discriminator="kind")]
STREAM = EventStream(Messages)

Others = Annotated[Greeting | Unrelated, Field(discriminator="kind")]
OTHER_STREAM = EventStream(Others)


def _streamed_fields(event: SentEvent[Messages]) -> dict[str, str]:
    app = FastAPI()

    @app.get("/events", response_class=EventSourceResponse)
    async def stream() -> AsyncIterator[SentEvent[Messages]]:
        yield event

    response = TestClient(app).get("/events")
    return dict(line.split(": ", 1) for line in response.text.splitlines() if line)


def test_encoded_message_streams_as_event_named_by_its_discriminator_with_json_data() -> None:
    fields = _streamed_fields(STREAM.encode(Reading(value=0.5)))

    assert (fields["event"], fields["data"]) == ("reading", '{"kind":"reading","value":0.5}')


def test_event_encoded_without_id_streams_no_id() -> None:
    fields = _streamed_fields(STREAM.encode(Reading(value=0.5)))

    assert "id" not in fields


def test_id_given_to_an_event_reaches_the_wire_unchanged() -> None:
    fields = _streamed_fields(STREAM.encode(Reading(value=0.5), id="run-7:a"))

    assert fields["id"] == "run-7:a"


def _encode_rejects_a_message_outside_the_union() -> None:
    STREAM.encode(Unrelated())  # type: ignore[arg-type]


async def _stream_rejects_an_event_of_another_stream() -> AsyncIterator[SentEvent[Messages]]:
    yield OTHER_STREAM.encode(Unrelated())  # type: ignore[misc]


async def _stream_rejects_a_plain_event() -> AsyncIterator[SentEvent[Messages]]:
    yield ServerSentEvent(event="greeting", raw_data="{}", id="1")  # type: ignore[misc]


@pytest.mark.parametrize(
    "messages",
    [
        pytest.param(Greeting | Reading, id="plain union"),
        pytest.param(Annotated[Greeting | Reading, Field(title="x")], id="no discriminator"),
    ],
)
def test_union_without_discriminator_is_rejected(messages: TypeForm[Greeting | Reading]) -> None:
    with pytest.raises(TypeError):
        EventStream(messages)
