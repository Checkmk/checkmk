# cmk-fastapi

Helpers that fill gaps FastAPI leaves in typing and OpenAPI 3.2, for Checkmk's FastAPI apps.
Each helper names the gap it fills, so it can be dropped once FastAPI or the tooling closes it.

## Overview

Public surface:

- `cmk.fastapi.FastAPI` is a drop-in subclass of `fastapi.FastAPI` that writes OpenAPI 3.2.0.
  - Gap: FastAPI emits the 3.2 `itemSchema` of streams, but declares the document as 3.1.0.
  - Gap: FastAPI describes a stream of `ServerSentEvent`s with one generic item, whatever the events carry.
    The document of this app describes each route annotated to yield `SentEvent[M]` with one item per member of M: `event` is the member's discriminator value, `data` the member as JSON, referring to its schema in `components/schemas`.
    Building the document fails for such a route without `response_class=EventSourceResponse`, or if a member's schema clashes with another schema of the same name.
- `cmk.fastapi.sse` types Server-Sent Events streams, on top of `fastapi.sse`.
  - Gap: a `ServerSentEvent` carries any data, so neither mypy nor the document know what a stream sends.
  - `EventStream(messages)` declares a stream of the union `messages`, an `Annotated[A | B, Field(discriminator=...)]`.
    `encode(message, id=None)` returns the `SentEvent` a route yields to send the message, with an `id:` field only if `id` is given.
    mypy rejects messages outside the union.
  - `SentEvent[M]` is an event of a stream of `M`, a `ServerSentEvent`.
    A route annotated to yield `SentEvent[M]` declares the stream, so mypy rejects events of other streams.

FastAPI does the rest of the stream: wire format, keepalive pings, `Cache-Control: no-cache` and `X-Accel-Buffering: no`.

openapi-typescript does not read OpenAPI 3.2 yet.
To generate TypeScript types, dump the document with `bazel/tools/dump_fastapi_openapi_spec.py`, which rewrites it to 3.1.

## Usage

```python
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, Field

from cmk.fastapi import FastAPI
from cmk.fastapi.sse import EventStream, SentEvent


class Ping(BaseModel):
    type: Literal["ping"] = "ping"


class Pong(BaseModel):
    type: Literal["pong"] = "pong"


Messages = Annotated[Ping | Pong, Field(discriminator="type")]
STREAM = EventStream(Messages)

app = FastAPI()


@app.get("/events", response_class=EventSourceResponse)
async def events() -> AsyncIterator[SentEvent[Messages]]:
    yield STREAM.encode(Ping(), id="1")
```

## Development

```sh
bazel test //packages/cmk-fastapi/...
bazel run //:format packages/cmk-fastapi
bazel lint //packages/cmk-fastapi/...
bazel build --config=mypy //packages/cmk-fastapi/...
```
