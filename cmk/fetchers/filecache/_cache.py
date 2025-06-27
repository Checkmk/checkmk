#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Persisted sections type and store.

Cache hierarchy

.. uml::

    abstract FileCache<TRawData> {
        + read(Mode) : TRawData | None
        + write(TRawData, Mode) : None
        - {abstract} _from_cache_file(bytes) : TRawData
        - {abstract} _to_cache_file(TRawData) : bytes
    }
    class AgentFileCache {
        - _from_cache_file(bytes) : TRawData
        - _to_cache_file(TRawData) : bytes
    }
    class NoCache {
        - _from_cache_file(bytes) : TRawData
        - _to_cache_file(TRawData) : bytes
    }
    class SNMPFileCache {
        - _from_cache_file(bytes) : TRawData
        - _to_cache_file(TRawData) : bytes
    }
    class TCPFetcher {}
    class ProgramFetcher {}
    class IPMIFetcher {}
    class SNMPFetcher {}
    class PiggybackFetcher {}

    FileCache <|.. AgentFileCache : <<bind>>\nTRawData::AgentRawData
    FileCache <|.. NoCache : <<bind>>\nTRawData::AgentRawData
    FileCache <|.. SNMPFileCache : <<bind>>\nTRawData::SNMPRawData
    AgentFileCache *-- TCPFetcher
    AgentFileCache *-- ProgramFetcher
    AgentFileCache *-- IPMIFetcher
    NoCache *-- PiggybackFetcher
    SNMPFileCache *-- SNMPFetcher

"""

from __future__ import annotations

import abc
import enum
import logging
import os
import time
from collections.abc import Sized
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Generic, NamedTuple, NoReturn, TypeVar

from cmk.ccc import store
from cmk.ccc.exceptions import MKFetcherError, MKGeneralException

from .._abstract import Mode

__all__ = [
    "FileCache",
    "FileCacheMode",
    "FileCacheOptions",
    "MaxAge",
    "NoCache",
]


TFileCache = TypeVar("TFileCache", bound="FileCache")
_TRawData = TypeVar("_TRawData", bound=Sized)


class MaxAge(NamedTuple):
    """Maximum age allowed for the cached data, in seconds"""

    checking: float
    discovery: float
    inventory: float

    @classmethod
    def zero(cls) -> MaxAge:
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def unlimited(cls) -> MaxAge:
        return cls(float("inf"), float("inf"), float("inf"))

    def get(self, mode: Mode, *, default: float = 0.0) -> float:
        return self._asdict().get(mode.name.lower(), default)


@enum.unique
class FileCacheMode(enum.IntFlag):
    DISABLED = enum.auto()
    READ = enum.auto()
    WRITE = enum.auto()
    READ_WRITE = READ | WRITE


class FileCache(Generic[_TRawData], abc.ABC):
    def __init__(
        self,
        *,
        path_template: str,
        max_age: MaxAge,
        simulation: bool,
        use_only_cache: bool,
        file_cache_mode: FileCacheMode | int,
    ) -> None:
        super().__init__()
        self.path_template: Final = path_template
        self.max_age = max_age
        # TODO(ml): Make sure simulation and use_only_cache are identical
        #           and find a better, more generic name such as "force"
        #           to produce the intended behavior.
        self.simulation = simulation
        self.use_only_cache = use_only_cache
        self.file_cache_mode = FileCacheMode(file_cache_mode)
        self._logger: Final = logging.getLogger("cmk.helper")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"path_template={self.path_template}",
                    f"max_age={self.max_age}",
                    f"simulation={self.simulation}",
                    f"use_only_cache={self.use_only_cache}",
                    f"file_cache_mode={self.file_cache_mode.value}",
                )
            )
            + ")"
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all(
            (
                self.path_template == other.path_template,
                self.max_age == other.max_age,
                self.simulation == other.simulation,
                self.use_only_cache == other.use_only_cache,
                self.file_cache_mode == other.file_cache_mode,
            )
        )

    @staticmethod
    @abc.abstractmethod
    def _from_cache_file(raw_data: bytes) -> _TRawData:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _to_cache_file(raw_data: _TRawData) -> bytes:
        raise NotImplementedError()

    def _do_cache(self, mode: Mode) -> bool:
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

    def read(self, mode: Mode) -> _TRawData | None:
        self._logger.debug("Read from cache: %r", self)
        raw_data = self._read(mode)
        if raw_data is not None:
            self._logger.debug("Got %r bytes data from cache", len(raw_data))
            return raw_data

        if self.simulation:
            raise MKFetcherError("No cached data available (caching enforced via simulation mode)")

        if self.use_only_cache:
            raise MKFetcherError("No cached data available")

        return raw_data

    def _make_path(self, mode: Mode) -> Path:
        # This is a kind of arbitrary mini-language but explicit in the
        # caller and easy to extend in the future.  If somebody has a
        # better idea to allow a serializable and parametrizable path
        # creation, that's fine with me.
        return Path(self.path_template.format(mode=mode.name.lower()))

    def _read(self, mode: Mode) -> _TRawData | None:
        if FileCacheMode.READ not in self.file_cache_mode or not self._do_cache(mode):
            return None

        path = self._make_path(mode)
        try:
            cachefile_age = time.time() - path.stat().st_mtime
        except FileNotFoundError:
            self._logger.debug("Not using cache (does not exist)")
            return None

        if cachefile_age > self.max_age.get(mode):
            self._logger.debug(
                "Not using cache (Too old. Age is %d sec, allowed is %s sec)",
                cachefile_age,
                self.max_age.get(mode),
            )
            return None

        # TODO: Use some generic store file read function to generalize error handling,
        # but there is currently no function that simply reads data from the file
        try:
            cache_file = path.read_bytes()
        except FileNotFoundError:
            self._logger.debug("Not using cache (Does not exist)")
            return None

        if not cache_file:
            self._logger.debug("Not using cache (Empty)")
            return None

        self._logger.debug("Using data from cache file %s", path)
        return self._from_cache_file(cache_file)

    def write(self, raw_data: _TRawData, mode: Mode) -> None:
        if FileCacheMode.WRITE not in self.file_cache_mode or not self._do_cache(mode):
            return
        path = self._make_path(mode)
        self._logger.debug("Write data to cache file %s", path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            store.RealIo(path).write(self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException(f"Cannot write cache file {path}: {e}")


class NoCache(FileCache[_TRawData]):
    def __init__(self, *args: object, **kw: object) -> None:
        super().__init__(
            path_template=str(os.devnull),
            max_age=MaxAge.zero(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

    @staticmethod
    def _from_cache_file(raw_data: object) -> NoReturn:
        raise TypeError("NoCache")

    @staticmethod
    def _to_cache_file(raw_data: _TRawData) -> NoReturn:
        raise TypeError("NoCache")


@dataclass(frozen=True, kw_only=True)
class FileCacheOptions:
    # TODO(ml): Split between fetcher and checker options; maybe also find
    # better names.

    # Set by the user via command line to prevent using cached information at all.
    disabled: bool = False
    # Is set by the "--cache" command line. This makes the caching logic use
    # cache files that are even older than the max_cachefile_age of the host/mode.
    use_outdated: bool = False
    # Set by the --no-tcp option from discovery, inventory, inventory as check,
    # and dump agent.
    tcp_use_only_cache: bool = False
    # Currently not (yet) used
    # I think this should be a fetcher option: "allow_live_fetching"
    use_only_cache: bool = False
    # Set by the --force option from inventory.
    keep_outdated: bool = False

    def file_cache_mode(self) -> FileCacheMode:
        return FileCacheMode.DISABLED if self.disabled else FileCacheMode.READ_WRITE
