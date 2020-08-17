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
from cmk.utils.log import VERBOSE

from .type_defs import BoundedAbstractRawData


class MKFetcherError(MKException):
    """An exception common to the fetchers."""


TFetcher = TypeVar("TFetcher", bound="ABCFetcher")


class ABCFetcher(Generic[BoundedAbstractRawData], metaclass=abc.ABCMeta):
    """Interface to the data fetchers."""
    @classmethod
    @abc.abstractmethod
    def from_json(cls: Type[TFetcher], serialized: Dict[str, Any]) -> TFetcher:
        """Deserialize from JSON."""
        return cls(**serialized)  # type: ignore[call-arg]

    @abc.abstractmethod
    def __enter__(self) -> 'ABCFetcher':
        """Prepare the data source."""

    @abc.abstractmethod
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> Optional[bool]:
        """Destroy the data source."""

    @abc.abstractmethod
    def data(self) -> BoundedAbstractRawData:
        """Return the data from the source."""


class ABCFileCache(Generic[BoundedAbstractRawData], metaclass=abc.ABCMeta):
    def __init__(
        self,
        *,
        path: Union[str, Path],
        max_age: Optional[int],
        disabled: bool,
        use_outdated: bool,
        simulation: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)
        self.max_age: Final = max_age
        self.disabled: Final = disabled
        self.use_outdated: Final = use_outdated
        self.simulation: Final = simulation
        self._logger: Final = logger

    @classmethod
    def from_json(cls, serialized: Dict[str, Any], logger: logging.Logger) -> "ABCFileCache":
        return cls(logger=logger, **serialized)

    @staticmethod
    @abc.abstractmethod
    def _from_cache_file(raw_data: bytes) -> BoundedAbstractRawData:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _to_cache_file(raw_data: BoundedAbstractRawData) -> bytes:
        raise NotImplementedError()

    def read(self) -> Optional[BoundedAbstractRawData]:
        assert self.max_age is not None
        if not self.path.exists():
            self._logger.debug("Not using cache (Does not exist)")
            return None

        if self.disabled:
            self._logger.debug("Not using cache (Cache usage disabled)")
            return None

        if self.simulation:
            self._logger.debug("Not using cache (Don't try it)")
            return None

        may_use_outdated = self.simulation or self.use_outdated
        cachefile_age = cmk.utils.cachefile_age(self.path)
        if not may_use_outdated and cachefile_age > self.max_age:
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

    def write(self, raw_data: BoundedAbstractRawData) -> None:
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
