#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, override

import fastapi
from fastapi.dependencies.utils import get_stream_item_type, get_typed_return_annotation
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.openapi.models import Components
from fastapi.routing import APIRoute, iter_route_contexts, RouteContext
from pydantic import BaseModel, TypeAdapter

from cmk.fastapi.sse import SentEvent

_MEDIA_TYPE = "text/event-stream"


class FastAPI(fastapi.FastAPI):
    """A `fastapi.FastAPI` writing OpenAPI 3.2, in which a route yielding `SentEvent[M]`
    describes one stream item per member of the discriminated union M."""

    _described_schema: dict[str, object] | None = None

    @override
    def setup(self) -> None:
        # `fastapi.FastAPI.__init__` sets `openapi_version` right before calling `setup`.
        self.openapi_version = "3.2.0"
        super().setup()

    @override
    def openapi(self) -> dict[str, Any]:  # type: ignore[explicit-any]
        schema = super().openapi()
        if schema is self._described_schema:
            return schema
        streams = list(_event_streams(iter_route_contexts(self.routes)))
        schemas = _merged_schemas(schema.get("components", {}).get("schemas", {}), streams)
        items = [
            (media, stream.item_schema)
            for stream in streams
            for method in stream.methods
            for response in schema["paths"][stream.path][method.lower()]["responses"].values()
            if (media := response.get("content", {}).get(_MEDIA_TYPE)) is not None
        ]
        for media, item_schema in items:
            media["itemSchema"] = item_schema
        if schemas:
            schema.setdefault("components", {})["schemas"] = schemas
        self._described_schema = schema
        return schema


@dataclass(frozen=True)
class _EventStream:
    at: str
    path: str
    methods: frozenset[str]
    item_schema: dict[str, object]
    schemas: Mapping[str, object]


def _event_streams(routes: Iterable[RouteContext]) -> Iterator[_EventStream]:
    for route in routes:
        match route:
            case RouteContext(
                original_route=APIRoute(endpoint=endpoint),
                path_format=str(path),
                methods=set(methods),
                include_in_schema=True,
            ):
                item = get_stream_item_type(get_typed_return_annotation(endpoint))
                if isinstance(item, type) and issubclass(item, SentEvent):
                    at = f"{' '.join(sorted(methods))} {path}"
                    if not route.is_sse_stream:
                        raise TypeError(
                            f"{at} yields events, serve it with response_class=EventSourceResponse"
                        )
                    yield _event_stream(at, path, frozenset(methods), item)
            case _:
                pass


def _event_stream(
    at: str, path: str, methods: frozenset[str], item: type[SentEvent[BaseModel]]
) -> _EventStream:
    match item.__pydantic_generic_metadata__["args"]:
        case (messages,):
            schema = TypeAdapter(messages).json_schema(  # nosemgrep: type-adapter-detected
                mode="serialization", ref_template=REF_TEMPLATE
            )
        case _:
            schema = {}
    match schema:
        case {"discriminator": {"mapping": dict() as mapping}}:
            return _EventStream(
                at=at,
                path=path,
                methods=methods,
                item_schema={"oneOf": [_event_schema(name, ref) for name, ref in mapping.items()]},
                schemas=jsonable_encoder(
                    Components(schemas=schema.get("$defs", {})), by_alias=True, exclude_none=True
                )["schemas"],
            )
        case _:
            raise TypeError(
                f"{at} yields {item.__name__}, expected the events of a discriminated union"
            )


def _event_schema(name: object, ref: object) -> dict[str, object]:
    return {
        "type": "object",
        "required": ["event", "data"],
        "properties": {
            "event": {"const": name},
            "data": {
                "type": "string",
                "contentMediaType": "application/json",
                "contentSchema": {"$ref": ref},
            },
            "id": {"type": "string"},
        },
    }


def _merged_schemas(
    schemas: Mapping[str, object], streams: Sequence[_EventStream]
) -> dict[str, object]:
    merged = dict(schemas)
    for stream in streams:
        for name, schema in stream.schemas.items():
            if merged.setdefault(name, schema) != schema:
                raise ValueError(
                    f"{stream.at} sends a {name} that clashes with the schema of that name"
                )
    return {name: merged[name] for name in sorted(merged)}
