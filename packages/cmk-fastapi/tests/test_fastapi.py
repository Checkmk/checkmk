#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import AsyncIterator
from typing import Annotated, Literal

import pytest
from fastapi.sse import EventSourceResponse
from openapi_spec_validator import OpenAPIV32SpecValidator
from pydantic import BaseModel, Field

from cmk.fastapi import FastAPI
from cmk.fastapi.sse import EventStream, SentEvent


class Greeting(BaseModel):
    kind: Literal["greeting"] = "greeting"
    text: str


class Reading(BaseModel):
    kind: Literal["reading"] = "reading"
    value: float


Messages = Annotated[Greeting | Reading, Field(discriminator="kind")]
STREAM = EventStream(Messages)


def _stream_app() -> FastAPI:
    app = FastAPI()

    @app.get("/events", response_class=EventSourceResponse)
    async def stream() -> AsyncIterator[SentEvent[Messages]]:
        yield STREAM.encode(Reading(value=0.5))

    return app


def _clashing_app() -> FastAPI:
    app = _stream_app()

    class Reading(BaseModel):
        level: int

    @app.get("/reading")
    def reading() -> Reading:
        return Reading(level=1)

    return app


def test_spec_validates_as_openapi_3_2() -> None:
    spec = _stream_app().openapi()

    OpenAPIV32SpecValidator(spec).validate()


def test_spec_describes_each_member_as_an_item_with_its_schema_as_data() -> None:
    spec = _stream_app().openapi()

    assert spec["paths"]["/events"]["get"]["responses"]["200"]["content"]["text/event-stream"] == {
        "itemSchema": {
            "oneOf": [
                {
                    "type": "object",
                    "required": ["event", "data"],
                    "properties": {
                        "event": {"const": "greeting"},
                        "data": {
                            "type": "string",
                            "contentMediaType": "application/json",
                            "contentSchema": {"$ref": "#/components/schemas/Greeting"},
                        },
                        "id": {"type": "string"},
                    },
                },
                {
                    "type": "object",
                    "required": ["event", "data"],
                    "properties": {
                        "event": {"const": "reading"},
                        "data": {
                            "type": "string",
                            "contentMediaType": "application/json",
                            "contentSchema": {"$ref": "#/components/schemas/Reading"},
                        },
                        "id": {"type": "string"},
                    },
                },
            ]
        }
    }


def test_spec_lists_the_member_schemas_as_components() -> None:
    spec = _stream_app().openapi()

    assert spec["components"]["schemas"].keys() == {"Greeting", "Reading"}


def test_member_shared_with_another_route_is_listed_once() -> None:
    class Note(BaseModel):
        kind: Literal["note"] = "note"
        text: str | None = None

    Notes = Annotated[Note | Reading, Field(discriminator="kind")]
    app = FastAPI()

    @app.get("/events", response_class=EventSourceResponse)
    async def stream() -> AsyncIterator[SentEvent[Notes]]:
        yield EventStream(Notes).encode(Note())

    @app.get("/note")
    def note() -> Note:
        return Note()

    spec = app.openapi()

    assert spec["components"]["schemas"].keys() == {"Note", "Reading"}


def test_stream_route_without_event_source_response_breaks_the_spec() -> None:
    app = FastAPI()

    @app.get("/events")
    async def stream() -> AsyncIterator[SentEvent[Messages]]:
        yield STREAM.encode(Reading(value=0.5))

    with pytest.raises(TypeError, match="GET /events .* response_class=EventSourceResponse"):
        app.openapi()


def test_member_clashing_with_another_schema_of_its_name_breaks_the_spec() -> None:
    app = _clashing_app()

    with pytest.raises(ValueError, match="GET /events sends a Reading"):
        app.openapi()


def test_spec_breaks_again_after_a_broken_build() -> None:
    app = _clashing_app()
    with contextlib.suppress(ValueError):
        app.openapi()

    with pytest.raises(ValueError, match="GET /events sends a Reading"):
        app.openapi()
