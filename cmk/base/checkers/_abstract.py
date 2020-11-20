#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import logging
import sys
from functools import partial
from pathlib import Path
from typing import cast, final, Final, Generic, MutableMapping, Optional, Set, TypeVar, Union

import cmk.utils
import cmk.utils.debug
import cmk.utils.log  # TODO: Remove this!
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKIPAddressLookupError, MKSNMPError, MKTimeout
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    result,
    SectionName,
    ServiceCheckResult,
    SourceType,
)

from cmk.snmplib.type_defs import TRawData

from cmk.fetchers import ABCFetcher, ABCFileCache, MKFetcherError
from cmk.fetchers.controller import FetcherType
from cmk.fetchers.type_defs import Mode

import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
from cmk.base.check_utils import PiggybackRawData, SectionCacheInfo, TSectionContent
from cmk.base.config import HostConfig
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData

from ._cache import PersistedSections

__all__ = [
    "NO_SELECTION",
    "HostSections",
    "SectionNameCollection",
    "Source",
    "FileCacheFactory",
    "Mode",
    "set_cache_opts",
]


class SelectionType(enum.Enum):
    NONE = enum.auto()


SectionNameCollection = Union[SelectionType, Set[SectionName]]
# If preselected sections are given, we assume that we are interested in these
# and only these sections, so we may omit others and in the SNMP case (TODO (mo))
# must try to fetch them (regardles of detection).

NO_SELECTION: Final = SelectionType.NONE

THostSections = TypeVar("THostSections", bound="HostSections")


class HostSections(Generic[TSectionContent], metaclass=abc.ABCMeta):
    """A wrapper class for the host information read by the data sources

    It contains the following information:

        1. sections:                A dictionary from section_name to a list of rows,
                                    the section content
        2. piggybacked_raw_data:    piggy-backed data for other hosts
        3. cache_info:              Agent cache information
                                    (dict section name -> (cached_at, cache_interval))
    """
    def __init__(
        self,
        sections: Optional[MutableMapping[SectionName, TSectionContent]] = None,
        *,
        cache_info: Optional[SectionCacheInfo] = None,
        piggybacked_raw_data: Optional[PiggybackRawData] = None,
    ) -> None:
        super().__init__()
        self.sections = sections if sections else {}
        self.cache_info = cache_info if cache_info else {}
        self.piggybacked_raw_data = piggybacked_raw_data if piggybacked_raw_data else {}

    def __repr__(self):
        return "%s(sections=%r, cache_info=%r, piggybacked_raw_data=%r)" % (
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
        )

    def filter(self, selection: SectionNameCollection) -> "HostSections[TSectionContent]":
        """Filter for preselected sections"""
        # This could be optimized by telling the parser object about the
        # preselected sections and dismissing raw data at an earlier stage.
        # For now we don't need that, so we keep it simple.
        if selection is NO_SELECTION:
            return self
        return HostSections(
            {k: v for k, v in self.sections.items() if k in selection},
            cache_info={k: v for k, v in self.cache_info.items() if k in selection},
            piggybacked_raw_data={
                k: v for k, v in self.piggybacked_raw_data.items() if SectionName(k) in selection
            },
        )

    # TODO: It should be supported that different sources produce equal sections.
    # this is handled for the self.sections data by simply concatenating the lines
    # of the sections, but for the self.cache_info this is not done. Why?
    # TODO: checking.execute_check() is using the oldest cached_at and the largest interval.
    #       Would this be correct here?
    def add(self, host_sections: "HostSections") -> None:
        """Add the content of `host_sections` to this HostSection."""
        for section_name, section_content in host_sections.sections.items():
            self.sections.setdefault(
                section_name,
                cast(TSectionContent, []),
            ).extend(section_content)  # type: ignore[arg-type]

        for hostname, raw_lines in host_sections.piggybacked_raw_data.items():
            self.piggybacked_raw_data.setdefault(hostname, []).extend(raw_lines)

        if host_sections.cache_info:
            self.cache_info.update(host_sections.cache_info)

    def add_persisted_sections(
        self,
        persisted_sections: PersistedSections[TSectionContent],
        *,
        logger: logging.Logger,
    ) -> None:
        """Add information from previous persisted infos."""
        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue  # Skip entries of "old" format

            # Don't overwrite sections that have been received from the source with this call
            if section_name in self.sections:
                logger.debug("Skipping persisted section %r, live data available", section_name)
                continue

            logger.debug("Using persisted section %r", section_name)
            persisted_from, persisted_until, section = entry
            self.cache_info[section_name] = (persisted_from, persisted_until - persisted_from)
            self.sections[section_name] = section


class Parser(Generic[TRawData, THostSections], metaclass=abc.ABCMeta):
    """Parse raw data into host sections."""
    @abc.abstractmethod
    def parse(self, raw_data: TRawData, *, selection: SectionNameCollection) -> THostSections:
        raise NotImplementedError


def set_cache_opts(use_caches: bool) -> None:
    # TODO check these settings vs.
    # cmk/base/automations/check_mk.py:_set_cache_opts_of_checkers
    if use_caches:
        FileCacheFactory.maybe = True
        FileCacheFactory.use_outdated = True


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
    def make(self) -> ABCFileCache[TRawData]:
        raise NotImplementedError


class Source(Generic[TRawData, THostSections], metaclass=abc.ABCMeta):
    """Hold the configuration to fetchers and checkers.

    At best, this should only hold static data, that is, every
    attribute is final.

    """
    use_outdated_persisted_sections: bool = False

    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        source_type: SourceType,
        fetcher_type: FetcherType,
        description: str,
        default_raw_data: TRawData,
        default_host_sections: THostSections,
        id_: str,
        cache_dir: Optional[Path] = None,
        persisted_section_dir: Optional[Path] = None,
    ) -> None:
        self.hostname: Final[str] = hostname
        self.ipaddress: Final[Optional[str]] = ipaddress
        self.mode: Final[Mode] = mode
        self.source_type: Final[SourceType] = source_type
        self.fetcher_type: Final[FetcherType] = fetcher_type
        self.description: Final[str] = description
        self.default_raw_data: Final = default_raw_data
        self.default_host_sections: Final[THostSections] = default_host_sections
        self.id: Final[str] = id_
        if not cache_dir:
            cache_dir = Path(cmk.utils.paths.data_source_cache_dir) / self.id
        if not persisted_section_dir:
            persisted_section_dir = Path(cmk.utils.paths.var_dir) / "persisted_sections" / self.id

        self.file_cache_path: Final[Path] = cache_dir / self.hostname
        self.file_cache_max_age: int = 0
        self.persisted_sections_file_path: Final[Path] = persisted_section_dir / self.hostname

        self.host_config: Final[HostConfig] = HostConfig.make_host_config(hostname)
        self._logger: Final[logging.Logger] = logging.getLogger("cmk.base.data_source.%s" % id_)

        self.exit_spec = self.host_config.exit_code_spec(id_)

    def __repr__(self) -> str:
        return "%s(%r, %r, mode=%r, description=%r, id=%r)" % (
            type(self).__name__,
            self.hostname,
            self.ipaddress,
            self.mode,
            self.description,
            self.id,
        )

    @property
    def fetcher_configuration(self):
        return self._make_fetcher().to_json()

    @final
    def fetch(self) -> result.Result[TRawData, Exception]:
        try:
            with self._make_fetcher() as fetcher:
                return fetcher.fetch(self.mode)
        except Exception as exc:
            if cmk.utils.debug.enabled():
                raise
            return result.Error(exc)

    @final
    def parse(
        self,
        raw_data: result.Result[TRawData, Exception],
        *,
        selection: SectionNameCollection,
    ) -> result.Result[THostSections, Exception]:
        try:
            return raw_data.map(partial(self._make_parser().parse, selection=selection))
        except Exception as exc:
            self._logger.log(VERBOSE, "ERROR: %s", exc)
            if cmk.utils.debug.enabled():
                raise
            return result.Error(exc)

    @final
    def summarize(
        self,
        host_sections: result.Result[THostSections, Exception],
    ) -> ServiceCheckResult:
        summarizer = self._make_summarizer()
        return host_sections.fold(
            ok=summarizer.summarize_success,
            error=summarizer.summarize_failure,
        )

    @abc.abstractmethod
    def _make_file_cache(self) -> ABCFileCache[TRawData]:
        raise NotImplementedError

    @abc.abstractmethod
    def _make_fetcher(self) -> ABCFetcher:
        """Create a fetcher with this configuration."""
        raise NotImplementedError

    @abc.abstractmethod
    def _make_parser(self) -> "Parser[TRawData, THostSections]":
        """Create a parser with this configuration."""
        raise NotImplementedError

    @abc.abstractmethod
    def _make_summarizer(self) -> "Summarizer[THostSections]":
        """Create a summarizer with this configuration."""
        raise NotImplementedError

    def _setup_logger(self) -> None:
        """Add the source log prefix to the class logger"""
        self._logger.propagate = False
        handler = logging.StreamHandler(stream=sys.stdout)
        fmt = " %s[%s%s%s]%s %%(message)s" % (tty.bold, tty.normal, self.id, tty.bold, tty.normal)
        handler.setFormatter(logging.Formatter(fmt))
        del self._logger.handlers[:]  # Remove all previously existing handlers
        self._logger.addHandler(handler)


class Summarizer(Generic[THostSections], metaclass=abc.ABCMeta):
    """Class to summarize parsed data into a ServiceCheckResult."""
    def __init__(self, exit_spec: config.ExitSpec) -> None:
        super().__init__()
        self.exit_spec: Final[config.ExitSpec] = exit_spec

    @abc.abstractmethod
    def summarize_success(self, host_sections: THostSections) -> ServiceCheckResult:
        raise NotImplementedError

    def summarize_failure(self, exc: Exception) -> ServiceCheckResult:
        status = self._extract_status(exc)
        return status, str(exc) + check_api_utils.state_markers[status], []

    def _extract_status(self, exc: Exception) -> int:
        if isinstance(exc, MKEmptyAgentData):
            return self.exit_spec.get("empty_output", 2)
        if isinstance(exc, (
                MKAgentError,
                MKFetcherError,
                MKIPAddressLookupError,
                MKSNMPError,
        )):
            return self.exit_spec.get("connection", 2)
        if isinstance(exc, MKTimeout):
            return self.exit_spec.get("timeout", 2)
        return self.exit_spec.get("exception", 3)
