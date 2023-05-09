#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from contextlib import suppress
from typing import Any, Iterator, Type, TypeVar

__all__ = ["Protocol"]

TProtocol = TypeVar("TProtocol", bound="Protocol")


class Protocol(abc.ABC):
    """Base class for serializable data.

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

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls: Type[TProtocol], data: bytes) -> TProtocol:
        raise NotImplementedError
