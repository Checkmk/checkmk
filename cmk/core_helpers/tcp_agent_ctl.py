#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import zlib
from enum import Enum
from typing import Final, Iterator

from cmk.utils.type_defs.protocol import Deserializer, Serializer


class Version(
    bytes,
    Enum,
):
    V1 = b"\0\0"

    @staticmethod
    def length() -> int:
        return 2


class CompressionType(
    bytes,
    Enum,
):
    UNCOMPRESSED = b"\0"
    ZLIB = b"\1"

    @staticmethod
    def length() -> int:
        return 1


class AgentCtlMessage(Deserializer):
    def __init__(
        self,
        version: Version,
        payload: bytes,
    ) -> None:
        super().__init__()
        self.version: Final = version
        self.payload: Final = payload

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
    ) -> AgentCtlMessage:
        version = Version(data[: Version.length()])
        remaining_data = data[len(version) :]
        if version is Version.V1:
            return cls(
                version,
                MessageV1.from_bytes(remaining_data).payload,
            )
        # unreachable
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(
            (
                hash(self.version),
                hash(self.payload),
            )
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(
            __o,
            AgentCtlMessage,
        ):
            return self.version == __o.version and self.payload == __o.payload
        return False


class HeaderV1(Serializer, Deserializer):
    def __init__(
        self,
        compression_type: CompressionType,
    ) -> None:
        super().__init__()
        self.compression_type: Final = compression_type

    def __iter__(self) -> Iterator[bytes]:
        yield self.compression_type

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
    ) -> HeaderV1:
        return cls(CompressionType(data[: CompressionType.length()]))


class MessageV1(Deserializer):
    def __init__(
        self,
        header: HeaderV1,
        payload: bytes,
    ) -> None:
        super().__init__()
        self.header: Final = header
        self.payload: Final = payload

    @classmethod
    def from_bytes(cls, data: bytes) -> MessageV1:
        return cls(
            header := HeaderV1.from_bytes(data),
            _decompress(
                header.compression_type,
                data[len(header) :],
            ),
        )

    def __hash__(self) -> int:
        return hash(
            (
                hash(self.header),
                hash(self.payload),
            )
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(
            __o,
            MessageV1,
        ):
            return self.header == __o.header and self.payload == __o.payload
        return False


def _decompress(
    compression_type: CompressionType,
    data: bytes,
) -> bytes:
    if compression_type is CompressionType.ZLIB:
        try:
            return zlib.decompress(data)
        except zlib.error as e:
            raise ValueError(f"Decompression with zlib failed: {e!r}") from e
    return data
