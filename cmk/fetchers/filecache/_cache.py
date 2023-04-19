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
import copy
import enum
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Generic, NamedTuple, NoReturn, TypeVar

import cmk.utils
import cmk.utils.paths
import cmk.utils.store as _store
from cmk.utils.exceptions import MKFetcherError, MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostName

from cmk.snmplib.type_defs import TRawData

from .._abstract import Mode

__all__ = [
    "FileCache",
    "FileCacheMode",
    "FileCacheOptions",
    "MaxAge",
    "NoCache",
]


TFileCache = TypeVar("TFileCache", bound="FileCache")


class MaxAge(NamedTuple):
    """Maximum age allowed for the cached data, in seconds.

    See Also:
        cmk.base.config.max_cachefile_age() for the default values configured.

    """

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


class FileCache(Generic[TRawData], abc.ABC):
    def __init__(
        self,
        hostname: HostName,
        *,
        path_template: str,
        max_age: MaxAge,
        simulation: bool,
        use_only_cache: bool,
        file_cache_mode: FileCacheMode | int,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
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
                    f"{self.hostname}",
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
                self.hostname == other.hostname,
                self.path_template == other.path_template,
                self.max_age == other.max_age,
                self.simulation == other.simulation,
                self.use_only_cache == other.use_only_cache,
                self.file_cache_mode == other.file_cache_mode,
            )
        )

    def to_json(self) -> Mapping[str, Any]:
        return {
            "hostname": str(self.hostname),
            "path_template": self.path_template,
            "max_age": self.max_age,
            "simulation": self.simulation,
            "use_only_cache": self.use_only_cache,
            "file_cache_mode": self.file_cache_mode,
        }

    @classmethod
    def from_json(cls: type[TFileCache], serialized: Mapping[str, Any]) -> TFileCache:
        serialized_ = copy.deepcopy(dict(serialized))
        max_age = MaxAge(*serialized_.pop("max_age"))
        return cls(max_age=max_age, **serialized_)

    @staticmethod
    @abc.abstractmethod
    def _from_cache_file(raw_data: bytes) -> TRawData:
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _to_cache_file(raw_data: TRawData) -> bytes:
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

    def read(self, mode: Mode) -> TRawData | None:
        self._logger.debug("Read from cache: %r", self)
        raw_data = self._read(mode)
        if raw_data is not None:
            self._logger.debug("Got %r bytes data from cache", len(raw_data))
            return raw_data

        if self.simulation:
            raise MKFetcherError("Got no data (Simulation mode enabled and no cached data present)")

        if self.use_only_cache:
            raise MKFetcherError("Got no data (use_only_cache)")

        return raw_data

    @staticmethod
    def _make_path(template: str, *, hostname: HostName, mode: Mode) -> Path:
        # This is a kind of arbitrary mini-language but explicit in the
        # caller and easy to extend in the future.  If somebody has a
        # better idea to allow a serializable and parametrizable path
        # creation, that's fine with me.
        return Path(template.format(mode=mode.name.lower(), hostname=hostname))

    def _read(self, mode: Mode) -> TRawData | None:
        if FileCacheMode.READ not in self.file_cache_mode or not self._do_cache(mode):
            return None

        path = self._make_path(self.path_template, hostname=self.hostname, mode=mode)
        try:
            cachefile_age = cmk.utils.cachefile_age(path)
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

        self._logger.log(VERBOSE, "Using data from cache file %s", path)
        return self._from_cache_file(cache_file)

    def write(self, raw_data: TRawData, mode: Mode) -> None:
        if FileCacheMode.WRITE not in self.file_cache_mode or not self._do_cache(mode):
            return

        path = self._make_path(self.path_template, hostname=self.hostname, mode=mode)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise MKGeneralException(f"Cannot create directory {path.parent!r}: {e}")

        self._logger.debug("Write data to cache file %s", path)
        try:
            _store.save_bytes_to_file(path, self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException(f"Cannot write cache file {path}: {e}")


class NoCache(FileCache[TRawData]):
    def __init__(self, hostname: HostName, *args: object, **kw: object) -> None:
        super().__init__(
            hostname,
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
    def _to_cache_file(raw_data: TRawData) -> NoReturn:
        raise TypeError("NoCache")


class FileCacheOptions(NamedTuple):
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
