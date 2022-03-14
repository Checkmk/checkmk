#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from contextlib import suppress
from typing import Any, Iterator, Protocol, Type, TypeVar

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

    def __eq__(self, other: Any) -> bool:
        with suppress(TypeError):
            return bytes(self) == bytes(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(bytes(self))

    def __add__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(self) + bytes(other)
        return NotImplemented

    def __radd__(self, other: Any) -> bytes:
        with suppress(TypeError):
            return bytes(other) + bytes(self)
        return NotImplemented

    def __len__(self) -> int:
        return len(bytes(self))

    def __bytes__(self) -> bytes:
        return b"".join(self)

    @abc.abstractmethod
    def __iter__(self) -> Iterator[bytes]:
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
    def from_bytes(cls: Type[TDeserializer], data: bytes) -> TDeserializer:
        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other: Any) -> bool:
        return NotImplemented

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError
