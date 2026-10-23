#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, get_args, get_origin, TYPE_CHECKING

from fastapi.sse import ServerSentEvent
from pydantic import BaseModel
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from typing_extensions import TypeForm


class SentEvent[M: BaseModel](ServerSentEvent):  # type: ignore[explicit-any]
    pass


class EventStream[M: BaseModel]:
    def __init__(self, messages: TypeForm[M]) -> None:
        self._discriminator = _discriminator(messages)

    def encode(self, message: M, id: str | None = None) -> SentEvent[M]:  # noqa: A002
        dumped = message.model_dump(mode="json", include={self._discriminator})
        return SentEvent(
            event=dumped[self._discriminator],
            raw_data=message.model_dump_json(by_alias=True),
            id=id,
        )


def _discriminator(messages: object) -> str:
    if get_origin(messages) is Annotated:
        for metadata in get_args(messages)[1:]:
            if isinstance(metadata, FieldInfo) and isinstance(metadata.discriminator, str):
                return metadata.discriminator
    raise TypeError(f"Expected a union discriminated by a field, got {messages!r}")
