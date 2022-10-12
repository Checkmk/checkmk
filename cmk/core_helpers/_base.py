#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from functools import partial
from typing import Any, final, Generic, Literal, Mapping, Optional, Type, TypeVar

from cmk.utils.exceptions import MKFetcherError, MKIPAddressLookupError
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostAddress, result

from cmk.snmplib.type_defs import TRawData

from .cache import FileCache
from .host_sections import HostSections, TRawDataSection
from .type_defs import Mode, SectionNameCollection

__all__ = [
    "Fetcher",
    "verify_ipaddress",
    "get_raw_data",
]

TFetcher = TypeVar("TFetcher", bound="Fetcher")


class Fetcher(Generic[TRawData], abc.ABC):
    """Interface to the data fetchers."""

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()
        self._logger = logger

    @final
    @classmethod
    def from_json(cls: Type[TFetcher], serialized: Mapping[str, Any]) -> TFetcher:
        """Deserialize from JSON."""
        return cls._from_json(serialized)

    @classmethod
    @abc.abstractmethod
    def _from_json(cls: Type[TFetcher], serialized: Mapping[str, Any]) -> TFetcher:
        raise NotImplementedError()

    @abc.abstractmethod
    def to_json(self) -> Mapping[str, Any]:
        """Serialize to JSON."""
        raise NotImplementedError()

    @final
    def __enter__(self) -> "Fetcher[TRawData]":
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
    def fetch(self, mode: Mode) -> result.Result[TRawData, Exception]:
        """Return the data from the source, either cached or from IO."""
        try:
            return result.OK(self._fetch(mode))
        except Exception as exc:
            return result.Error(exc)

    def _fetch(self, mode: Mode) -> TRawData:
        self._logger.log(VERBOSE, "[%s] Execute data source", self.__class__.__name__)

        try:
            self.open()
            raw_data = self._fetch_from_io(mode)
        except MKFetcherError:
            raise
        except Exception as exc:
            raise MKFetcherError(repr(exc) if any(exc.args) else type(exc).__name__) from exc

        return raw_data

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()


def get_raw_data(
    file_cache: FileCache[TRawData], fetcher: Fetcher[TRawData], mode: Mode
) -> result.Result[TRawData, Exception]:
    try:
        cached = file_cache.read(mode)
        if cached is not None:
            return result.OK(cached)

        if file_cache.simulation:
            raise MKFetcherError(f"{fetcher}: data unavailable in simulation mode")

        fetched: result.Result[TRawData, Exception] = result.Error(
            MKFetcherError(f"{fetcher}: unknown error")
        )
        with fetcher:
            fetched = fetcher.fetch(mode)
        fetched.map(partial(file_cache.write, mode=mode))
        return fetched

    except Exception as exc:
        return result.Error(exc)


class Parser(Generic[TRawData, TRawDataSection], abc.ABC):
    """Parse raw data into host sections."""

    @abc.abstractmethod
    def parse(
        self, raw_data: TRawData, *, selection: SectionNameCollection
    ) -> HostSections[TRawDataSection]:
        raise NotImplementedError


def verify_ipaddress(address: Optional[HostAddress]) -> None:
    if not address:
        raise MKIPAddressLookupError("Host has no IP address configured.")

    if address in ["0.0.0.0", "::"]:
        raise MKIPAddressLookupError(
            "Failed to lookup IP address and no explicit IP address configured"
        )
