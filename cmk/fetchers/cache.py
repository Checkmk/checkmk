#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Persisted sections type and store."""

import abc
import itertools
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    Final,
    Generic,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import cmk.utils
import cmk.utils.store as _store
from cmk.utils.log import VERBOSE
from cmk.utils.exceptions import MKGeneralException, MKFetcherError
from cmk.utils.type_defs import AgentRawDataSection, SectionName

from cmk.snmplib.type_defs import SNMPRawDataSection, TRawData

__all__ = [
    "ABCRawDataSection",
    "FileCache",
    "FileCacheFactory",
    "PersistedSections",
    "SectionStore",
    "set_cache_opts",
    "TRawDataSection",
]

# ABCRawDataSection is wrong from a typing point of view.
# AgentRawDataSection and SNMPRawDataSection are not correct either.
ABCRawDataSection = Union[AgentRawDataSection, SNMPRawDataSection]
TRawDataSection = TypeVar("TRawDataSection", bound=ABCRawDataSection)


class PersistedSections(
        Generic[TRawDataSection],
        MutableMapping[SectionName, Tuple[int, int, TRawDataSection]],
):
    __slots__ = ("_store",)

    def __init__(self, store: MutableMapping[SectionName, Tuple[int, int, TRawDataSection]]):
        self._store = store

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._store)

    def __getitem__(self, key: SectionName) -> Tuple[int, int, TRawDataSection]:
        return self._store.__getitem__(key)

    def __setitem__(self, key: SectionName, value: Tuple[int, int, TRawDataSection]) -> None:
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
        sections: Mapping[SectionName, TRawDataSection],
        interval_lookup: Mapping[SectionName, Optional[int]],
        *,
        cached_at: int,
    ) -> "PersistedSections[TRawDataSection]":
        self = cls({})
        for section_name, section_content in sections.items():
            fetch_interval = interval_lookup[section_name]
            if fetch_interval is None:
                continue
            self[section_name] = (cached_at, fetch_interval, section_content)

        return self

    def cached_at(self, section_name: SectionName) -> int:
        entry = self[section_name]
        if len(entry) == 2:
            return 0
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
            {SectionName(k): v for k, v in raw_sections_data.items()})


TFileCache = TypeVar("TFileCache", bound="FileCache")


def set_cache_opts(use_caches: bool) -> None:
    # TODO check these settings vs.
    # cmk/base/automations/check_mk.py:_set_cache_opts_of_checkers
    if use_caches:
        FileCacheFactory.maybe = True
        FileCacheFactory.use_outdated = True


class FileCache(Generic[TRawData], abc.ABC):
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
        self._logger: Final[logging.Logger] = logging.getLogger("cmk.helper")

    def __repr__(self) -> str:
        return "%s(path=%r, max_age=%r, disabled=%r, use_outdated=%r, simulation=%r" % (
            type(self).__name__,
            self.path,
            self.max_age,
            self.disabled,
            self.use_outdated,
            self.simulation,
        )

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
        cache_file = self.path.read_bytes()
        if not cache_file:
            self._logger.debug("Not using cache (Empty)")
            return None

        self._logger.log(VERBOSE, "Using data from cache file %s", self.path)
        return self._from_cache_file(cache_file)

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
            _store.save_file(self.path, self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (self.path, e))


class FileCacheFactory(Generic[TRawData], abc.ABC):
    """Factory / configuration to FileCache."""

    # TODO: Clean these options up! We need to change all call sites to use
    #       a single Checkers() object during processing first. Then we
    #       can change these class attributes to object attributes.
    #
    # Set by the user via command line to prevent using cached information at all.
    # Is also set by inventory for SNMP checks to handle the special situation that
    # the inventory is not allowed to use the regular checking based SNMP data source
    # cache.
    disabled: bool = False
    snmp_disabled: bool = False
    agent_disabled: bool = False
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
        path: Union[Path, str],
        *,
        max_age: int,
        simulation: bool = False,
    ):
        super().__init__()
        self.path: Final[Path] = Path(path)
        self.max_age: Final[int] = max_age
        self.simulation: Final[bool] = simulation

    @classmethod
    def reset_maybe(cls):
        cls.maybe = not cls.disabled

    @abc.abstractmethod
    def make(self) -> FileCache[TRawData]:
        raise NotImplementedError
