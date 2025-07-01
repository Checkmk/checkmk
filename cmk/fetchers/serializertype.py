#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Buffer, Iterator
from typing import Protocol, Self, SupportsBytes, TypeVar

__all__ = ["Serializer", "Deserializer"]


class Serializer(Protocol):
    """Base class for serializable data.

    Implementations have the following requirements:

    * They must be immutable.
    * If both `Serializer` and `Deserializer` are defined, then
    `bytes(Serializer(Deserializer.from_bytes(x))) == x` must hold
    for any valid `x`.


    Note:
        This should be usable as a type. Do not add any
        concrete implementation here.
    """

    def __eq__(self, other: object) -> bool:
        # Test both `Buffer` and `SupportsBytes`.
        #
        # `memoryview` doesn't have a `__bytes__()` method and therefore
        # tests false to `isinstance(..., SupportsBytes)` eventhough
        # `bytes(memoryview(b"hello"))` works as expected.
        if isinstance(other, Buffer | SupportsBytes):
            return bytes(self) == bytes(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(bytes(self))

    def __add__(self, other: Buffer | SupportsBytes) -> bytes:
        return bytes(self) + bytes(other)

    def __radd__(self, other: Buffer | SupportsBytes) -> bytes:
        return bytes(other) + bytes(self)

    def __len__(self) -> int:
        return sum(len(memoryview(b)) for b in self)

    def __bytes__(self) -> bytes:
        return b"".join(self)

    @abc.abstractmethod
    def __iter__(self) -> Iterator[Buffer]:
        raise NotImplementedError


TDeserializer = TypeVar("TDeserializer", bound="Deserializer")


class Deserializer(Protocol):
    """Base class for deserializable data.

    Implementations have the same requirements as Serializer.

    Note:
        This should be usable as a type. Do not add any
        concrete implementation here.

    """

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, data: Buffer) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        return NotImplemented

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError
