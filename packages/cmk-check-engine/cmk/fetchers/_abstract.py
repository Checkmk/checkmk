#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import abc
import enum
from collections.abc import Buffer, Iterator
from typing import final, Literal, Protocol, Self, SupportsBytes

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import MKTimeout
from cmk.helper_interface import FetcherError

__all__ = ["Fetcher", "Mode", "Serializer", "Deserializer"]


class Mode(enum.Enum):
    NONE = enum.auto()
    CHECKING = enum.auto()
    DISCOVERY = enum.auto()
    INVENTORY = enum.auto()
    RTC = enum.auto()
    # Special case for discovery/checking/inventory command line argument where we specify in
    # advance all sections we want. Should disable caching, and in the SNMP case also detection.
    # Disabled sections must *not* be discarded in this mode.
    FORCE_SECTIONS = enum.auto()


class Fetcher[TRawData](abc.ABC):
    """Interface to the data fetchers."""

    @final
    def __enter__(self) -> "Fetcher[TRawData]":
        return self

    @final
    def __exit__(self, *exc_info: object) -> Literal[False]:
        """Close the data source."""
        self.close()
        return False

    @abc.abstractmethod
    def open(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def close(self) -> None:
        raise NotImplementedError()

    @final
    def fetch(self, mode: Mode) -> result.Result[TRawData, Exception]:
        """Return the data from the source, either cached or from IO."""
        try:
            self.open()
            return result.OK(self._fetch_from_io(mode))
        except MKTimeout:
            raise
        except FetcherError:
            raise
        except Exception as exc:
            return result.Error(FetcherError(repr(exc) if any(exc.args) else type(exc).__name__))

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()


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
