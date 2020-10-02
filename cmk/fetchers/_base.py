#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import itertools
import logging
from pathlib import Path
from types import TracebackType
from typing import Any, Literal, Dict, final, Final, Generic, Optional, Type, TypeVar, Union

import cmk.utils
import cmk.utils.store as store
from cmk.utils.exceptions import MKException, MKGeneralException, MKIPAddressLookupError
from cmk.utils.log import logger as cmk_logger
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import ErrorResult, HostAddress, OKResult, Result

from cmk.snmplib.type_defs import TRawData

from .type_defs import Mode

__all__ = ["ABCFetcher", "ABCFileCache", "MKFetcherError", "verify_ipaddress"]


class MKFetcherError(MKException):
    """An exception common to the fetchers."""


TFileCache = TypeVar("TFileCache", bound="ABCFileCache")


class ABCFileCache(Generic[TRawData], abc.ABC):
    def __init__(
        self,
        *,
        path: Union[str, Path],
        max_age: int,
        disabled: bool,
        use_outdated: bool,
        simulation: bool,
    ) -> None:
        super().__init__()
        self.path: Final[Path] = Path(path)
        self.max_age: Final[int] = max_age
        self.disabled: Final[bool] = disabled
        self.use_outdated: Final[bool] = use_outdated
        self.simulation: Final[bool] = simulation
        self._logger: Final[logging.Logger] = cmk_logger

    def __hash__(self) -> int:
        *_rest, last = itertools.accumulate(
            (self.path, self.max_age, self.disabled, self.use_outdated, self.simulation),
            lambda acc, elem: acc ^ hash(elem),
            initial=0,
        )
        return last

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all((
            self.path == other.path,
            self.max_age == other.max_age,
            self.disabled == other.disabled,
            self.use_outdated == other.use_outdated,
            self.simulation == other.simulation,
        ))

    def to_json(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "max_age": self.max_age,
            "disabled": self.disabled,
            "use_outdated": self.use_outdated,
            "simulation": self.simulation,
        }

    @classmethod
    def from_json(cls: Type[TFileCache], serialized: Dict[str, Any]) -> TFileCache:
        return cls(**serialized)

    @staticmethod
    @abc.abstractmethod
    def _from_cache_file(raw_data: bytes) -> TRawData:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _to_cache_file(raw_data: TRawData) -> bytes:
        raise NotImplementedError()

    def read(self) -> Optional[TRawData]:
        raw_data = self._read()
        if raw_data is None and self.simulation:
            raise MKFetcherError("Got no data (Simulation mode enabled and no cachefile present)")
        return raw_data

    def _read(self) -> Optional[TRawData]:
        if not self.path.exists():
            self._logger.debug("Not using cache (Does not exist)")
            return None

        if self.disabled:
            self._logger.debug("Not using cache (Cache usage disabled)")
            return None

        may_use_outdated = self.simulation or self.use_outdated
        cachefile_age = cmk.utils.cachefile_age(self.path)
        if not may_use_outdated and cachefile_age > self.max_age:
            self._logger.debug(
                "Not using cache (Too old. Age is %d sec, allowed is %s sec)",
                cachefile_age,
                self.max_age,
            )
            return None

        # TODO: Use some generic store file read function to generalize error handling,
        # but there is currently no function that simply reads data from the file
        result = self.path.read_bytes()
        if not result:
            self._logger.debug("Not using cache (Empty)")
            return None

        self._logger.log(VERBOSE, "Using data from cache file %s", self.path)
        return self._from_cache_file(result)

    def write(self, raw_data: TRawData) -> None:
        if self.disabled:
            self._logger.debug("Not writing data to cache file (Cache usage disabled)")
            return

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise MKGeneralException("Cannot create directory %r: %s" % (self.path.parent, e))

        self._logger.debug("Write data to cache file %s", self.path)
        try:
            store.save_file(self.path, self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (self.path, e))


TFetcher = TypeVar("TFetcher", bound="ABCFetcher")


class ABCFetcher(Generic[TRawData], metaclass=abc.ABCMeta):
    """Interface to the data fetchers."""
    def __init__(self, file_cache: ABCFileCache, logger: logging.Logger) -> None:
        super().__init__()
        self.file_cache: Final[ABCFileCache[TRawData]] = file_cache
        self._logger = logger

    @classmethod
    @abc.abstractmethod
    def from_json(cls: Type[TFetcher], serialized: Dict[str, Any]) -> TFetcher:
        """Deserialize from JSON."""
        raise NotImplementedError()

    @abc.abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """Serialize to JSON."""
        raise NotImplementedError()

    @final
    def __enter__(self) -> 'ABCFetcher':
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
    def fetch(self, mode: Mode) -> Result[TRawData, Exception]:
        """Return the data from the source, either cached or from IO."""
        try:
            return OKResult(self._fetch(mode))
        except Exception as exc:
            if cmk.utils.debug.enabled():
                raise
            return ErrorResult(exc)

    @abc.abstractmethod
    def _is_cache_enabled(self, mode: Mode) -> bool:
        """Decide whether to try to read data from cache"""
        raise NotImplementedError()

    def _fetch(self, mode: Mode) -> TRawData:
        # TODO(ml): EAFP would significantly simplify the code.
        if self.file_cache.simulation or self._is_cache_enabled(mode):
            raw_data = self._fetch_from_cache()
            if raw_data:
                self._logger.log(VERBOSE, "[%s] Use cached data", self.__class__.__name__)
                return raw_data

        self._logger.log(VERBOSE, "[%s] Execute data source", self.__class__.__name__)
        raw_data = self._fetch_from_io(mode)
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
