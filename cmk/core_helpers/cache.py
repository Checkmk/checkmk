#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Persisted sections type and store.

Cache hierarchy

.. uml::

    abstract FileCache<TRawData> {
        + read(Mode) : Optional[TRawData]
        + write(TRawData, Mode) : None
        + {abstract} make_path(Mode) : Path
        - {abstract} _from_cache_file(bytes) : TRawData
        - {abstract} _to_cache_file(TRawData) : bytes
    }
    abstract AgentFileCache {}
    class DefaultAgentFileCache {
        + make_path(Mode) : Path
        - _from_cache_file(bytes) : TRawData
        - _to_cache_file(TRawData) : bytes
    }
    class NoCache {
        + make_path(Mode) : Path
        - _from_cache_file(bytes) : TRawData
        - _to_cache_file(TRawData) : bytes
    }
    class SNMPFileCache {
        + make_path(Mode) : Path
        - _from_cache_file(bytes) : TRawData
        - _to_cache_file(TRawData) : bytes
    }
    class TCPFetcher {}
    class ProgramFetcher {}
    class IPMIFetcher {}
    class SNMPFetcher {}
    class PiggybackFetcher {}

    FileCache <|.. AgentFileCache : <<bind>>\nTRawData::AgentRawData
    FileCache <|.. SNMPFileCache : <<bind>>\nTRawData::SNMPRawData
    AgentFileCache <|-- DefaultAgentFileCache
    AgentFileCache <|-- NoCache
    DefaultAgentFileCache *-- TCPFetcher
    DefaultAgentFileCache *-- ProgramFetcher
    DefaultAgentFileCache *-- IPMIFetcher
    NoCache *-- PiggybackFetcher
    SNMPFileCache *-- SNMPFetcher

"""

import abc
import copy
import logging
from pathlib import Path
from typing import (
    Any,
    Callable,
    Final,
    Generic,
    Iterator,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

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
    "FileCacheFactory",
    "PersistedSections",
    "SectionStore",
    "TRawDataSection",
]

# ABCRawDataSection is wrong from a typing point of view.
# AgentRawDataSection and SNMPRawDataSection are not correct either.
ABCRawDataSection = Union[AgentRawDataSection, SNMPRawDataSection]
TRawDataSection = TypeVar("TRawDataSection", bound=ABCRawDataSection)


class PersistedSections(  # pylint: disable=too-many-ancestors
    Generic[TRawDataSection],
    MutableMapping[SectionName, Tuple[int, int, Sequence[TRawDataSection]]],
):
    __slots__ = ("_store",)

    def __init__(
        self, store: MutableMapping[SectionName, Tuple[int, int, Sequence[TRawDataSection]]]
    ):
        self._store = store

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._store)

    def __getitem__(self, key: SectionName) -> Tuple[int, int, Sequence[TRawDataSection]]:
        return self._store.__getitem__(key)

    def __setitem__(
        self, key: SectionName, value: Tuple[int, int, Sequence[TRawDataSection]]
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
        lookup_persist: Callable[[SectionName], Optional[Tuple[int, int]]],
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
        path: Union[str, Path],
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
        cache_info: MutableMapping[SectionName, Tuple[int, int]],
        lookup_persist: Callable[[SectionName], Optional[Tuple[int, int]]],
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
        lookup_persist: Callable[[SectionName], Optional[Tuple[int, int]]],
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
        cache_info: MutableMapping[SectionName, Tuple[int, int]],
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


class FileCache(Generic[TRawData], abc.ABC):
    def __init__(
        self,
        hostname: HostName,
        *,
        base_path: Union[str, Path],
        max_age: MaxAge,
        disabled: bool,
        use_outdated: bool,
        simulation: bool,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.base_path: Final = Path(base_path)
        self.max_age = max_age
        self.disabled = disabled
        self.use_outdated = use_outdated
        self.simulation = simulation
        self._logger: Final = logging.getLogger("cmk.helper")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"{self.hostname}",
                    f"base_path={self.base_path}",
                    f"max_age={self.max_age}",
                    f"disabled={self.disabled}",
                    f"use_outdated={self.use_outdated}",
                    f"simulation={self.simulation}",
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
                self.base_path == other.base_path,
                self.max_age == other.max_age,
                self.disabled == other.disabled,
                self.use_outdated == other.use_outdated,
                self.simulation == other.simulation,
            )
        )

    def to_json(self) -> Mapping[str, Any]:
        return {
            "hostname": str(self.hostname),
            "base_path": str(self.base_path),
            "max_age": self.max_age,
            "disabled": self.disabled,
            "use_outdated": self.use_outdated,
            "simulation": self.simulation,
        }

    @classmethod
    def from_json(cls: Type[TFileCache], serialized: Mapping[str, Any]) -> TFileCache:
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
        if not self._do_cache(mode):
            return None

        path = self.make_path(mode)
        if not path.exists():
            if self.simulation:
                raise MKFetcherError(
                    "Got no data (Simulation mode enabled and no cachefile present)"
                )
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
        if not self._do_cache(mode):
            return

        path = self.make_path(mode)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise MKGeneralException("Cannot create directory %r: %s" % (path.parent, e))

        self._logger.debug("Write data to cache file %s", path)
        try:
            _store.save_bytes_to_file(path, self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (path, e))


class FileCacheFactory(Generic[TRawData], abc.ABC):
    """Factory / configuration to FileCache."""

    # TODO: Clean these options up! We need to change all call sites to use
    #       a single Checkers() object during processing first. Then we
    #       can change these class attributes to object attributes.
    #
    # Set by the user via command line to prevent using cached information at all.
    disabled: bool = False
    # Set by the code in different situations where we recommend, but not enforce,
    # to use the cache. The user can always use "--cache" to override this.
    # It's used to 'transport' caching opt between modules, eg:
    # - modes: FileCacheFactory.maybe = use_caches
    # - discovery: use_caches = FileCacheFactory.maybe
    maybe = False
    # Is set by the "--cache" command line. This makes the caching logic use
    # cache files that are even older than the max_cachefile_age of the host/mode.
    use_outdated = False

    def __init__(
        self,
        hostname: HostName,
        base_path: Union[Path, str],
        *,
        max_age: MaxAge,
        simulation: bool = False,
    ):
        super().__init__()
        self.hostname: Final = hostname
        self.base_path: Final[Path] = Path(base_path)
        self.max_age: Final = max_age
        self.simulation: Final[bool] = simulation

    @abc.abstractmethod
    def make(self, *, force_cache_refresh: bool = False) -> FileCache[TRawData]:
        raise NotImplementedError
