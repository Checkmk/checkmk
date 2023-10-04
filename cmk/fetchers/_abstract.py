#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import logging
from collections.abc import Mapping
from typing import Any, final, Generic, Literal, TypeVar

import cmk.utils.resulttype as result
from cmk.utils.exceptions import MKFetcherError, MKTimeout
from cmk.utils.log import VERBOSE

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

    def __init__(self, *, logger: logging.Logger) -> None:
        super().__init__()
        self._logger = logger

    @final
    @classmethod
    def from_json(cls: type[TFetcher], serialized: Mapping[str, Any]) -> TFetcher:
        """Deserialize from JSON."""
        return cls._from_json(serialized)

    @classmethod
    @abc.abstractmethod
    def _from_json(cls: type[TFetcher], serialized: Mapping[str, Any]) -> TFetcher:
        raise NotImplementedError()

    @abc.abstractmethod
    def to_json(self) -> Mapping[str, Any]:
        """Serialize to JSON."""
        raise NotImplementedError()

    @final
    def __enter__(self) -> "Fetcher[_TRawData]":
        return self

    @final
    def __exit__(self, *exc_info: object) -> Literal[True]:
        """Close the data source."""
        self.close()
        return True

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
            return result.OK(self._fetch(mode))
        except MKTimeout:
            raise
        except Exception as exc:
            return result.Error(exc)

    def _fetch(self, mode: Mode) -> _TRawData:
        self._logger.log(VERBOSE, "[%s] Execute data source", self.__class__.__name__)

        try:
            self.open()
            raw_data = self._fetch_from_io(mode)
        except MKTimeout:
            raise
        except MKFetcherError:
            raise
        except Exception as exc:
            raise MKFetcherError(repr(exc) if any(exc.args) else type(exc).__name__) from exc

        return raw_data

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> _TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()
