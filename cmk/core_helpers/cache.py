#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
from collections.abc import Callable, Iterator, Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any, Final, Generic, NamedTuple, TypeVar

import cmk.utils
import cmk.utils.store as _store
from cmk.utils.exceptions import MKFetcherError, MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostName, SectionName

from cmk.snmplib.type_defs import SNMPRawDataSection, TRawData

from .type_defs import AgentRawDataSection, Mode

__all__ = [
    "ABCRawDataSection",
    "FileCache",
    "FileCacheOptions",
    "PersistedSections",
    "SectionStore",
    "TRawDataSection",
]

# ABCRawDataSection is wrong from a typing point of view.
# AgentRawDataSection and SNMPRawDataSection are not correct either.
ABCRawDataSection = AgentRawDataSection | SNMPRawDataSection
TRawDataSection = TypeVar("TRawDataSection", bound=ABCRawDataSection)


class PersistedSections(  # pylint: disable=too-many-ancestors
    Generic[TRawDataSection],
    MutableMapping[SectionName, tuple[int, int, Sequence[TRawDataSection]]],
):
    __slots__ = ("_store",)

    def __init__(
        self, store: MutableMapping[SectionName, tuple[int, int, Sequence[TRawDataSection]]]
    ):
        self._store = store

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._store!r})"

    def __getitem__(self, key: SectionName) -> tuple[int, int, Sequence[TRawDataSection]]:
        return self._store.__getitem__(key)

    def __setitem__(
        self, key: SectionName, value: tuple[int, int, Sequence[TRawDataSection]]
    ) -> None:
        return self._store.__setitem__(key, value)

    def __delitem__(self, key: SectionName) -> None:
        return self._store.__delitem__(key)

    def __iter__(self) -> Iterator[SectionName]:
        return self._store.__iter__()

    def __len__(self) -> int:
        return self._store.__len__()

    @classmethod
    def from_sections(
        cls,
        *,
        sections: Mapping[SectionName, Sequence[TRawDataSection]],
        lookup_persist: Callable[[SectionName], tuple[int, int] | None],
    ) -> "PersistedSections[TRawDataSection]":
        return cls(
            {
                section_name: persist_info + (section_content,)
                for section_name, section_content in sections.items()
                if (persist_info := lookup_persist(section_name)) is not None
            }
        )

    def cached_at(self, section_name: SectionName) -> int:
        entry = self[section_name]
        if len(entry) == 2:
            return 0  # epoch? why?
        return entry[0]


class SectionStore(Generic[TRawDataSection]):
    def __init__(
        self,
        path: str | Path,
        *,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.path: Final = Path(path)
        self._logger: Final = logger

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path!r}, logger={self._logger!r})"

    def store(self, sections: PersistedSections[TRawDataSection]) -> None:
        if not sections:
            self._logger.debug("No persisted sections")
            self.path.unlink(missing_ok=True)
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        _store.save_object_to_file(
            self.path,
            {str(k): v for k, v in sections.items()},
            pretty=False,
        )
        self._logger.debug("Stored persisted sections: %s", ", ".join(str(s) for s in sections))

    def load(self) -> PersistedSections[TRawDataSection]:
        raw_sections_data = _store.load_object_from_file(self.path, default={})
        return PersistedSections[TRawDataSection](
            {SectionName(k): v for k, v in raw_sections_data.items()}
        )

    def update(
        self,
        sections: Mapping[SectionName, Sequence[TRawDataSection]],
        cache_info: MutableMapping[SectionName, tuple[int, int]],
        lookup_persist: Callable[[SectionName], tuple[int, int] | None],
        now: int,
        keep_outdated: bool,
    ) -> Mapping[SectionName, Sequence[TRawDataSection]]:
        persisted_sections = self._update(
            sections,
            lookup_persist,
            now=now,
            keep_outdated=keep_outdated,
        )
        return self._add_persisted_sections(
            sections,
            cache_info,
            persisted_sections,
        )

    def _update(
        self,
        sections: Mapping[SectionName, Sequence[TRawDataSection]],
        lookup_persist: Callable[[SectionName], tuple[int, int] | None],
        *,
        now: int,
        keep_outdated: bool,
    ) -> PersistedSections[TRawDataSection]:
        # TODO: This is not race condition free when modifying the data. Either remove
        # the possible write here and simply ignore the outdated sections or lock when
        # reading and unlock after writing
        persisted_sections = self.load()
        persisted_sections.update(
            PersistedSections[TRawDataSection].from_sections(
                sections=sections,
                lookup_persist=lookup_persist,
            )
        )
        if not keep_outdated:
            for section_name in tuple(persisted_sections):
                (_created_at, valid_until, _section_content) = persisted_sections[section_name]
                if valid_until < now:
                    del persisted_sections[section_name]

        self.store(persisted_sections)
        return persisted_sections

    def _add_persisted_sections(
        self,
        sections: Mapping[SectionName, Sequence[TRawDataSection]],
        cache_info: MutableMapping[SectionName, tuple[int, int]],
        persisted_sections: PersistedSections[TRawDataSection],
    ) -> Mapping[SectionName, Sequence[TRawDataSection]]:
        cache_info.update(
            {
                section_name: (created_at, valid_until - created_at)
                for section_name, (created_at, valid_until, *_rest) in persisted_sections.items()
                if section_name not in sections
            }
        )
        result: MutableMapping[SectionName, Sequence[TRawDataSection]] = dict(sections.items())
        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue  # Skip entries of "old" format

            # Don't overwrite sections that have been received from the source with this call
            if section_name in sections:
                self._logger.debug(
                    "Skipping persisted section %r, live data available",
                    section_name,
                )
                continue

            self._logger.debug("Using persisted section %r", section_name)
            result[section_name] = entry[-1]
        return result


TFileCache = TypeVar("TFileCache", bound="FileCache")


class MaxAge(NamedTuple):
    """Maximum age allowed for the cached data, in seconds.

    See Also:
        cmk.base.config.max_cachefile_age() for the default values configured.

    """

    checking: int
    discovery: int
    inventory: int

    @classmethod
    def none(cls):
        return cls(0, 0, 0)

    def get(self, mode: Mode, *, default: int = 0) -> int:
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
        use_outdated: bool,
        simulation: bool,
        use_only_cache: bool,
        file_cache_mode: FileCacheMode | int,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.path_template: Final = path_template
        self.max_age = max_age
        self.use_outdated = use_outdated
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
                    f"use_outdated={self.use_outdated}",
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
                self.use_outdated == other.use_outdated,
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
            "use_outdated": self.use_outdated,
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

        if not self.use_outdated and cachefile_age > self.max_age.get(mode):
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
    # Set by the --force option from inventory.
    keep_outdated: bool = False

    def file_cache_mode(self) -> FileCacheMode:
        return FileCacheMode.DISABLED if self.disabled else FileCacheMode.READ_WRITE
