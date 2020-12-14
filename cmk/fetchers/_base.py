#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from types import TracebackType
from typing import Any, Dict, final, Final, Generic, Literal, Optional, Type, TypeVar

import cmk.utils
from cmk.utils.exceptions import MKFetcherError, MKIPAddressLookupError
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostAddress, result

from cmk.snmplib.type_defs import TRawData

from .cache import FileCache
from .type_defs import Mode

__all__ = ["Fetcher", "verify_ipaddress"]

TFetcher = TypeVar("TFetcher", bound="Fetcher")


class Fetcher(Generic[TRawData], metaclass=abc.ABCMeta):
    """Interface to the data fetchers."""
    def __init__(self, file_cache: FileCache, logger: logging.Logger) -> None:
        super().__init__()
        self.file_cache: Final[FileCache[TRawData]] = file_cache
        self._logger = logger

    @final
    @classmethod
    def from_json(cls: Type[TFetcher], serialized: Dict[str, Any]) -> TFetcher:
        """Deserialize from JSON."""
        try:
            return cls._from_json(serialized)
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    @classmethod
    @abc.abstractmethod
    def _from_json(cls: Type[TFetcher], serialized: Dict[str, Any]) -> TFetcher:
        raise NotImplementedError()

    @abc.abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """Serialize to JSON."""
        raise NotImplementedError()

    @final
    def __enter__(self) -> 'Fetcher':
        """Prepare the data source."""
        try:
            self.open()
        except MKFetcherError:
            raise
        except Exception as exc:
            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError(repr(exc) if any(exc.args) else type(exc).__name__) from exc
        return self

    @final
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        """Destroy the data source."""
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
            return result.OK(self._fetch(mode))
        except Exception as exc:
            if cmk.utils.debug.enabled():
                raise
            return result.Error(exc)

    @abc.abstractmethod
    def _is_cache_read_enabled(self, mode: Mode) -> bool:
        """Decide whether to try to read data from cache"""
        raise NotImplementedError()

    @abc.abstractmethod
    def _is_cache_write_enabled(self, mode: Mode) -> bool:
        """Decide whether to write data to cache"""
        raise NotImplementedError()

    def _fetch(self, mode: Mode) -> TRawData:
        self._logger.debug("[%s] Fetch with cache settings: %r, Cache enabled: %r",
                           self.__class__.__name__, self.file_cache,
                           self._is_cache_read_enabled(mode))

        # TODO(ml): EAFP would significantly simplify the code.
        if self.file_cache.simulation or self._is_cache_read_enabled(mode):
            raw_data = self._fetch_from_cache()
            if raw_data:
                self._logger.log(VERBOSE, "[%s] Use cached data", self.__class__.__name__)
                return raw_data

        self._logger.log(VERBOSE, "[%s] Execute data source", self.__class__.__name__)
        raw_data = self._fetch_from_io(mode)
        if self._is_cache_write_enabled(mode):
            self.file_cache.write(raw_data)
        return raw_data

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()

    def _fetch_from_cache(self) -> Optional[TRawData]:
        return self.file_cache.read()


def verify_ipaddress(address: Optional[HostAddress]) -> None:
    if not address:
        raise MKIPAddressLookupError("Host has no IP address configured.")

    if address in ["0.0.0.0", "::"]:
        raise MKIPAddressLookupError(
            "Failed to lookup IP address and no explicit IP address configured")
