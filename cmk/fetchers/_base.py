#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, final, Final, NamedTuple, Generic, Literal, Optional, Type, TypeVar, Union

import cmk.utils
import cmk.utils.store as store
from cmk.utils.exceptions import MKFetcherError, MKGeneralException, MKIPAddressLookupError
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostAddress, result

from cmk.snmplib.type_defs import TRawData

from .type_defs import Mode

__all__ = ["ABCFetcher", "ABCFileCache", "MaxAge", "MKFetcherError", "verify_ipaddress"]


class MaxAge(NamedTuple):
    checking: int
    discovery: int
    inventory: int

    @classmethod
    def none(cls):
        return cls(0, 0, 0)

    def get(self, mode: Mode, *, default: int = 0) -> int:
        return self._asdict().get(mode.name.lower(), default)


TFileCache = TypeVar("TFileCache", bound="ABCFileCache")


class ABCFileCache(Generic[TRawData], abc.ABC):
    def __init__(
        self,
        *,
        base_path: Union[str, Path],
        max_age: MaxAge,
        disabled: bool,
        use_outdated: bool,
        simulation: bool,
    ) -> None:
        super().__init__()
        self.base_path: Final = Path(base_path)
        self.max_age = max_age
        self.disabled = disabled
        self.use_outdated = use_outdated
        self.simulation = simulation
        self._logger: Final[logging.Logger] = logging.getLogger("cmk.helper")

    def __repr__(self) -> str:
        return "%s(base_path=%r, max_age=%r, disabled=%r, use_outdated=%r, simulation=%r)" % (
            type(self).__name__,
            self.base_path,
            self.max_age,
            self.disabled,
            self.use_outdated,
            self.simulation,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all((
            self.base_path == other.base_path,
            self.max_age == other.max_age,
            self.disabled == other.disabled,
            self.use_outdated == other.use_outdated,
            self.simulation == other.simulation,
        ))

    def to_json(self) -> Dict[str, Any]:
        return {
            "base_path": str(self.base_path),
            "max_age": self.max_age,
            "disabled": self.disabled,
            "use_outdated": self.use_outdated,
            "simulation": self.simulation,
        }

    @classmethod
    def from_json(cls: Type[TFileCache], serialized: Dict[str, Any]) -> TFileCache:
        max_age = MaxAge(*serialized.pop("max_age"))
        return cls(max_age=max_age, **serialized)

    @staticmethod
    @abc.abstractmethod
    def _from_cache_file(raw_data: bytes) -> TRawData:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _to_cache_file(raw_data: TRawData) -> bytes:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def cache_read(mode: Mode) -> bool:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def cache_write(mode: Mode) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def make_path(self, mode: Mode) -> Path:
        raise NotImplementedError()

    def _do_cache(self, mode: Mode) -> bool:
        if self.disabled:
            self._logger.debug("Not using cache (Cache usage disabled)")
            return False

        if self.simulation:
            self._logger.debug("Using cache (Simulation mode)")
            return True

        if mode in {
                Mode.NONE,
                Mode.FORCE_SECTIONS,
                Mode.RTC,
        }:
            self._logger.debug("Not using cache (Mode %s)", mode)
            return False

        return True

    def read(self, mode: Mode) -> Optional[TRawData]:
        if not self._do_cache(mode) or not self.cache_read(mode):
            return None

        path = self.make_path(mode)
        if not path.exists():
            self._logger.debug("Not using cache (Does not exist)")
            return None

        may_use_outdated = self.simulation or self.use_outdated
        cachefile_age = cmk.utils.cachefile_age(path)
        if not may_use_outdated and cachefile_age > self.max_age.get(mode):
            self._logger.debug(
                "Not using cache (Too old. Age is %d sec, allowed is %s sec)",
                cachefile_age,
                self.max_age.get(mode),
            )
            return None

        raw_data = self._read(path)
        if raw_data is not None:
            self._logger.debug("Got %r bytes data from cache", len(raw_data))

        return raw_data

    def _read(self, path: Path) -> Optional[TRawData]:
        # TODO: Use some generic store file read function to generalize error handling,
        # but there is currently no function that simply reads data from the file
        cache_file = path.read_bytes()
        if not cache_file:
            self._logger.debug("Not using cache (Empty)")
            return None

        self._logger.log(VERBOSE, "Using data from cache file %s", path)
        return self._from_cache_file(cache_file)

    def write(self, raw_data: TRawData, mode: Mode) -> None:
        if not self._do_cache(mode) or not self.cache_write(mode):
            return

        path = self.make_path(mode)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise MKGeneralException("Cannot create directory %r: %s" % (path.parent, e))

        self._logger.debug("Write data to cache file %s", path)
        try:
            store.save_file(path, self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (path, e))


TFetcher = TypeVar("TFetcher", bound="ABCFetcher")


class ABCFetcher(Generic[TRawData], metaclass=abc.ABCMeta):
    """Interface to the data fetchers."""
    def __init__(self, file_cache: ABCFileCache, logger: logging.Logger) -> None:
        super().__init__()
        self.file_cache: Final[ABCFileCache[TRawData]] = file_cache
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
    def __enter__(self) -> 'ABCFetcher':
        return self

    @final
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        """Destroy the data source. Only needed if simulation mode is
        disabled"""
        if self.file_cache.simulation:
            return False

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

    def _fetch(self, mode: Mode) -> TRawData:
        self._logger.debug(
            "[%s] Fetch with cache settings: %r",
            self.__class__.__name__,
            self.file_cache,
        )
        raw_data = self.file_cache.read(mode)
        if raw_data is not None:
            self._logger.log(VERBOSE, "[%s] Use cached data", self.__class__.__name__)
            return raw_data

        if self.file_cache.simulation:
            raise MKFetcherError("Got no data (Simulation mode enabled and no cached data present)")

        self._logger.log(VERBOSE, "[%s] Execute data source", self.__class__.__name__)

        try:
            self.open()
            raw_data = self._fetch_from_io(mode)
        except MKFetcherError:
            raise
        except Exception as exc:
            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError(repr(exc) if any(exc.args) else type(exc).__name__) from exc

        self.file_cache.write(raw_data, mode)
        return raw_data

    @abc.abstractmethod
    def _fetch_from_io(self, mode: Mode) -> TRawData:
        """Override this method to contact the source and return the raw data."""
        raise NotImplementedError()


def verify_ipaddress(address: Optional[HostAddress]) -> None:
    if not address:
        raise MKIPAddressLookupError("Host has no IP address configured.")

    if address in ["0.0.0.0", "::"]:
        raise MKIPAddressLookupError(
            "Failed to lookup IP address and no explicit IP address configured")
