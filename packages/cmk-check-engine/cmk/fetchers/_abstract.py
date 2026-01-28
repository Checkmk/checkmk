#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import abc
import enum
from typing import final, Generic, Literal, TypeVar

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import MKTimeout
from cmk.helper_interface import FetcherError

__all__ = ["Fetcher", "Mode"]


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


TFetcher = TypeVar("TFetcher", bound="Fetcher")
_TRawData = TypeVar("_TRawData")


class Fetcher(Generic[_TRawData], abc.ABC):
    """Interface to the data fetchers."""

    @final
    def __enter__(self) -> "Fetcher[_TRawData]":
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
    def fetch(self, mode: Mode) -> result.Result[_TRawData, Exception]:
        """Return the data from the source, either cached or from IO."""
        try:
            self.open()
            return result.OK(self._fetch_from_io(mode))
        except MKTimeout:
            raise
        except Exception as exc:
            return result.Error(FetcherError(repr(exc) if any(exc.args) else type(exc).__name__))

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> _TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()
