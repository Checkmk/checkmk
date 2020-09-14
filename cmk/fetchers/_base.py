#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Final, Generic, Optional, Type, TypeVar, Union

import cmk.utils
import cmk.utils.store as store
from cmk.utils.exceptions import MKException, MKGeneralException
from cmk.utils.log import logger as cmk_logger
from cmk.utils.log import VERBOSE

from cmk.snmplib.type_defs import TRawData

from .type_defs import Mode

__all__ = ["ABCFetcher", "MKFetcherError"]


class MKFetcherError(MKException):
    """An exception common to the fetchers."""


TFileCache = TypeVar("TFileCache", bound="ABCFileCache")


class ABCFileCache(Generic[TRawData], metaclass=abc.ABCMeta):
    def __init__(
        self,
        *,
        path: Union[str, Path],
        max_age: Optional[int],
        disabled: bool,
        use_outdated: bool,
        simulation: bool,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)
        self.max_age = max_age
        self.disabled = disabled
        self.use_outdated = use_outdated
        self.simulation = simulation
        self._logger: Final = cmk_logger

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
        if not may_use_outdated and self.max_age is not None and cachefile_age > self.max_age:
            self._logger.debug("Not using cache (Too old. Age is %d sec, allowed is %s sec)",
                               cachefile_age, self.max_age)
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
        self.file_cache: ABCFileCache[TRawData] = file_cache
        self._logger = logger

    @classmethod
    @abc.abstractmethod
    def from_json(cls: Type[TFetcher], serialized: Dict[str, Any]) -> TFetcher:
        """Deserialize from JSON."""

    @abc.abstractmethod
    def __enter__(self) -> 'ABCFetcher':
        """Prepare the data source."""

    @abc.abstractmethod
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> Optional[bool]:
        """Destroy the data source."""

    @abc.abstractmethod
    def _use_cached_data(self, mode: Mode) -> bool:
        """Decide whether to try to read data from cache"""

    def fetch(self, mode: Mode) -> TRawData:
        """Return the data from the source, either cached or from IO."""
        # TODO(ml): EAFP would significantly simplify the code.
        if self._use_cached_data(mode):
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

    def _fetch_from_cache(self) -> Optional[TRawData]:
        return self.file_cache.read()
