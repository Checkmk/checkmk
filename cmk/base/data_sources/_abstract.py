#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import logging
import sys
from pathlib import Path
from typing import Any, cast, Dict, Final, Generic, Optional, Tuple, TypeVar, Union

import cmk.utils
import cmk.utils.debug
import cmk.utils.log  # TODO: Remove this!
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKSNMPError, MKTerminate, MKTimeout
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostAddress, HostName, SectionName, ServiceCheckResult, SourceType

from cmk.fetchers._base import ABCFileCache
from cmk.fetchers.controller import FetcherType
from cmk.fetchers.type_defs import BoundedAbstractRawData

import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.cpu_tracking as cpu_tracking
from cmk.base.check_utils import (
    BoundedAbstractPersistedSections,
    BoundedAbstractSectionContent,
    BoundedAbstractSections,
    PiggybackRawData,
    SectionCacheInfo,
)
from cmk.base.config import HostConfig, SelectedRawSections
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData, MKIPAddressLookupError

from ._cache import SectionStore

__all__ = ["ABCHostSections", "ABCConfigurator", "ABCDataSource", "Mode"]


class Mode(enum.Enum):
    NONE = enum.auto()
    CHECKING = enum.auto()
    DISCOVERY = enum.auto()
    INVENTORY = enum.auto()
    RTC = enum.auto()


class ABCHostSections(Generic[BoundedAbstractRawData, BoundedAbstractSections,
                              BoundedAbstractPersistedSections, BoundedAbstractSectionContent],
                      metaclass=abc.ABCMeta):
    """A wrapper class for the host information read by the data sources

    It contains the following information:

        1. sections:                A dictionary from section_name to a list of rows,
                                    the section content
        2. piggybacked_raw_data:    piggy-backed data for other hosts
        3. persisted_sections:      Sections to be persisted for later usage
        4. cache_info:              Agent cache information
                                    (dict section name -> (cached_at, cache_interval))
    """
    def __init__(
        self,
        sections: Optional[BoundedAbstractSections] = None,
        cache_info: Optional[SectionCacheInfo] = None,
        piggybacked_raw_data: Optional[PiggybackRawData] = None,
        persisted_sections: Optional[BoundedAbstractPersistedSections] = None,
    ) -> None:
        super().__init__()
        self.sections = sections if sections else {}
        self.cache_info = cache_info if cache_info else {}
        self.piggybacked_raw_data = piggybacked_raw_data if piggybacked_raw_data else {}
        self.persisted_sections = persisted_sections if persisted_sections else {}

    def __repr__(self):
        return "%s(sections=%r, cache_info=%r, piggybacked_raw_data=%r, persisted_sections=%r)" % (
            type(self).__name__,
            self.sections,
            self.cache_info,
            self.piggybacked_raw_data,
            self.persisted_sections,
        )

    # TODO: It should be supported that different sources produce equal sections.
    # this is handled for the self.sections data by simply concatenating the lines
    # of the sections, but for the self.cache_info this is not done. Why?
    # TODO: checking.execute_check() is using the oldest cached_at and the largest interval.
    #       Would this be correct here?
    def update(self, host_sections: "ABCHostSections") -> None:
        """Update this host info object with the contents of another one"""
        for section_name, section_content in host_sections.sections.items():
            self._extend_section(section_name, section_content)

        for hostname, raw_lines in host_sections.piggybacked_raw_data.items():
            self.piggybacked_raw_data.setdefault(hostname, []).extend(raw_lines)

        if host_sections.cache_info:
            self.cache_info.update(host_sections.cache_info)

        if host_sections.persisted_sections:
            self.persisted_sections.update(host_sections.persisted_sections)

    def add_persisted_sections(
        self,
        persisted_sections: BoundedAbstractPersistedSections,
        *,
        logger: logging.Logger,
    ) -> None:
        if not persisted_sections:
            return

        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue  # Skip entries of "old" format

            # Don't overwrite sections that have been received from the source with this call
            if section_name in self.sections:
                logger.debug("Skipping persisted section %r, live data available", section_name)
                continue

            logger.debug("Using persisted section %r", section_name)
            self._add_cached_section(section_name, *entry)

    def _extend_section(
        self,
        section_name: SectionName,
        section_content: BoundedAbstractSectionContent,
    ) -> None:
        self.sections.setdefault(section_name, []).extend(section_content)

    def _add_cached_section(
        self,
        section_name: SectionName,
        persisted_from: int,
        persisted_until: int,
        section: BoundedAbstractSectionContent,
    ) -> None:
        self.cache_info[section_name] = (persisted_from, persisted_until - persisted_from)
        # TODO: Find out why mypy complains about this
        self.sections[section_name] = section  # type: ignore[assignment]


BoundedAbstractHostSections = TypeVar("BoundedAbstractHostSections", bound=ABCHostSections)


class ABCParser(Generic[BoundedAbstractRawData, BoundedAbstractHostSections],
                metaclass=abc.ABCMeta):
    """Parse raw data into host sections."""
    def __init__(self, hostname: HostName, logger: logging.Logger) -> None:
        super().__init__()
        self.hostname: Final[HostName] = hostname
        self.host_config = config.HostConfig.make_host_config(self.hostname)
        self._logger = logger

    @abc.abstractmethod
    def parse(self, raw_data: BoundedAbstractRawData) -> BoundedAbstractHostSections:
        raise NotImplementedError


class ABCConfigurator(abc.ABC):
    """Hold the configuration to fetchers and checkers.

    At best, this should only hold static data, that is, every
    attribute is final.

    Dump the JSON configuration from `configure_fetcher()`.

    """
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        mode: Mode,
        source_type: SourceType,
        fetcher_type: FetcherType,
        description: str,
        id_: str,
        cpu_tracking_id: str,
        cache_dir: Optional[Path] = None,
        persisted_section_dir: Optional[Path] = None,
    ) -> None:
        self.hostname: Final[str] = hostname
        self.ipaddress: Final[Optional[str]] = ipaddress
        self.mode: Final[Mode] = mode
        self.source_type: Final[SourceType] = source_type
        self.fetcher_type: Final[FetcherType] = fetcher_type
        self.description: Final[str] = description
        self.id: Final[str] = id_
        self.cpu_tracking_id: Final[str] = cpu_tracking_id
        if not cache_dir:
            cache_dir = Path(cmk.utils.paths.data_source_cache_dir) / self.id
        if not persisted_section_dir:
            persisted_section_dir = Path(cmk.utils.paths.var_dir) / "persisted_sections" / self.id

        self.cache_file_path: Final[Path] = cache_dir / self.hostname
        self.persisted_sections_file_path: Final[Path] = persisted_section_dir / self.hostname

        self.host_config: Final[HostConfig] = HostConfig.make_host_config(hostname)
        self._logger: Final[logging.Logger] = logging.getLogger("cmk.base.data_source.%s" % id_)

    def __repr__(self) -> str:
        return "%s(%r, %r, mode=%r, description=%r, id=%r)" % (
            type(self).__name__,
            self.hostname,
            self.ipaddress,
            self.mode,
            self.description,
            self.id,
        )

    def _setup_logger(self) -> None:
        """Add the source log prefix to the class logger"""
        self._logger.propagate = False
        handler = logging.StreamHandler(stream=sys.stdout)
        fmt = " %s[%s%s%s]%s %%(message)s" % (tty.bold, tty.normal, self.id, tty.bold, tty.normal)
        handler.setFormatter(logging.Formatter(fmt))
        del self._logger.handlers[:]  # Remove all previously existing handlers
        self._logger.addHandler(handler)

    @abc.abstractmethod
    def configure_fetcher(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def make_checker(self) -> "ABCDataSource":
        raise NotImplementedError


class ABCSummarizer(Generic[BoundedAbstractHostSections], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def summarize(self, host_sections: BoundedAbstractHostSections) -> ServiceCheckResult:
        raise NotImplementedError


class ABCDataSource(Generic[BoundedAbstractRawData, BoundedAbstractSections,
                            BoundedAbstractPersistedSections, BoundedAbstractHostSections],
                    metaclass=abc.ABCMeta):
    """Base checker class."""

    # TODO: Clean these options up! We need to change all call sites to use
    #       a single DataSources() object during processing first. Then we
    #       can change these class attributes to object attributes.
    #
    # Set by the user via command line to prevent using cached information at all.
    # Is also set by inventory for SNMP checks to handle the special situation that
    # the inventory is not allowed to use the regular checking based SNMP data source
    # cache.
    _no_cache = False
    # Set by the code in different situations where we recommend, but not enforce,
    # to use the cache. The user can always use "--cache" to override this.
    _may_use_cache_file = False
    # Is set by the "--cache" command line. This makes the caching logic use
    # cache files that are even older than the max_cachefile_age of the host/mode.
    _use_outdated_cache_file = False
    _use_outdated_persisted_sections = False

    def __init__(
        self,
        configurator: ABCConfigurator,
        *,
        summarizer: ABCSummarizer,
        default_raw_data: BoundedAbstractRawData,
        default_host_sections: BoundedAbstractHostSections,
    ) -> None:
        super().__init__()
        self.configurator = configurator
        self.summarizer = summarizer
        self.default_raw_data: Final[BoundedAbstractRawData] = default_raw_data
        self.default_host_sections: Final[BoundedAbstractHostSections] = default_host_sections
        self._logger = self.configurator._logger
        self._section_store = SectionStore(
            self.configurator.persisted_sections_file_path,
            self._logger,
        )

        self._max_cachefile_age: Optional[int] = None

        # Runtime data (managed by self.run()) - Meant for self.get_summary_result()
        self._exception: Optional[Exception] = None
        self._host_sections: Optional[BoundedAbstractHostSections] = None

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.configurator)

    @property
    def hostname(self) -> HostName:
        return self.configurator.hostname

    @property
    def ipaddress(self) -> Optional[HostAddress]:
        return self.configurator.ipaddress

    @property
    def id(self) -> str:
        return self.configurator.id

    @property
    def description(self) -> str:
        return self.configurator.description

    @property
    def _cpu_tracking_id(self) -> str:
        return self.configurator.cpu_tracking_id

    def run(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> ABCHostSections:
        """
        :param selected_raw_section: A set of raw sections, that we
        are interested in.  If set, we assume that these sections should
        be produced if possible, and any raw section that is not listed
        here *may* be omitted.
        """
        result = self._run(
            selected_raw_sections=selected_raw_sections,
            get_raw_data=False,
        )
        if not isinstance(result, ABCHostSections):
            raise TypeError("Got invalid type: %r" % result)
        return result

    @cpu_tracking.track
    def _run(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
        get_raw_data: bool,
    ) -> Union[BoundedAbstractRawData, BoundedAbstractHostSections]:
        """Wrapper for self._execute() that unifies several things:

        a) Exception handling
        b) Caching of raw data

        Exceptions: All exceptions are caught and written to self._exception. The caller
        should use self.get_summary_result() to get the summary result of this data source
        which also includes information about the happed exception. In case the --debug
        mode is enabled, the exceptions are raised. self._exception is re-initialized
        to None when this method is called."""
        #
        # This function has two different functionalities depending on `get_raw_data`.
        #
        # In short, the code does (mind the types):
        #
        # def _run(self, *, ..., get_raw_data : Literal[True]) -> RawData:
        #     assert get_raw_data is True
        #     try:
        #         return fetcher.data()
        #     except:
        #         return self.default_raw_data
        #
        # *or*
        #
        # def _run(self, *, ..., get_raw_data : Literal[False]) -> HostSections:
        #     assert get_raw_data is False
        #     try:
        #         return self.parse(fetcher.data())
        #     except:
        #         return self.default_host_sections
        #
        # Also note that `get_raw_data()` is only used for Agent sources.
        #
        self._exception = None
        self._host_sections = None

        try:
            persisted_sections: BoundedAbstractPersistedSections = self._section_store.load(
                self._use_outdated_persisted_sections)

            raw_data, is_cached_data = self._get_raw_data(
                selected_raw_sections=selected_raw_sections,)

            self._host_sections = self._parser.parse(raw_data)
            assert isinstance(self._host_sections, ABCHostSections)

            if get_raw_data:
                return raw_data

            if self._host_sections.persisted_sections and not is_cached_data:
                persisted_sections.update(self._host_sections.persisted_sections)
                self._section_store.store(persisted_sections)

            # Add information from previous persisted infos
            self._host_sections.add_persisted_sections(
                persisted_sections,
                logger=self._logger,
            )

            return self._host_sections

        except MKTerminate:
            raise

        except Exception as e:
            self._logger.log(VERBOSE, "ERROR: %s", e)
            if cmk.utils.debug.enabled():
                raise
            self._exception = e

        if get_raw_data:
            return self.default_raw_data
        return self.default_host_sections

    def _get_raw_data(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> Tuple[BoundedAbstractRawData, bool]:
        """Returns the current raw data of this data source

        It either uses previously cached raw data of this data source or
        executes the data source to get new data.

        The "raw data" is the raw byte string returned by the source for
        AgentDataSource sources. The SNMPDataSource source already
        return the final info data structure.
        """
        raw_data = self._file_cache.read()
        if raw_data:
            self._logger.log(VERBOSE, "Use cached data")
            return raw_data, True

        if raw_data is None and config.simulation_mode:
            raise MKAgentError("Got no data (Simulation mode enabled and no cachefile present)")

        self._logger.log(VERBOSE, "Execute data source")
        raw_data = self._execute(selected_raw_sections=selected_raw_sections,)
        self._file_cache.write(raw_data)
        return raw_data, False

    @abc.abstractmethod
    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> BoundedAbstractRawData:
        """Fetches the current agent data from the source specified with
        hostname and ipaddress and returns the result as "raw data" that is
        later converted by self._parse() to a HostSection().

        The "raw data" is the raw byte string returned by the source for
        AgentDataSource sources. The SNMPDataSource source already
        return the final data structure to be wrapped into HostSections()."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _parser(self) -> ABCParser[BoundedAbstractRawData, BoundedAbstractHostSections]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def _file_cache(self) -> ABCFileCache:
        raise NotImplementedError

    def set_max_cachefile_age(self, max_cachefile_age: int) -> None:
        self._max_cachefile_age = max_cachefile_age

    @classmethod
    def disable_data_source_cache(cls) -> None:
        cls._no_cache = True

    @classmethod
    def is_agent_cache_disabled(cls) -> bool:
        return cls._no_cache

    @staticmethod
    def get_may_use_cache_file() -> bool:
        return ABCDataSource._may_use_cache_file

    @staticmethod
    def set_may_use_cache_file(state: bool = True) -> None:
        ABCDataSource._may_use_cache_file = state

    def get_summary_result(self) -> ServiceCheckResult:
        """Returns a three element tuple of state, output and perfdata (list) that summarizes
        the execution result of this data source.

        This is e.g. used for the output of the "Check_MK", "Check_MK Discovery" or
        "Check_MK HW/SW Inventory" services."""
        assert self.configurator.mode is not Mode.NONE

        if not self._exception:
            assert self._host_sections is not None
            return self.summarizer.summarize(self._host_sections)

        exc_msg = "%s" % self._exception

        if isinstance(self._exception, MKEmptyAgentData):
            status = self.configurator.host_config.exit_code_spec().get("empty_output", 2)

        elif isinstance(self._exception, (MKAgentError, MKIPAddressLookupError, MKSNMPError)):
            status = self.configurator.host_config.exit_code_spec().get("connection", 2)

        elif isinstance(self._exception, MKTimeout):
            status = self.configurator.host_config.exit_code_spec().get("timeout", 2)

        else:
            status = self.configurator.host_config.exit_code_spec().get("exception", 3)
        status = cast(int, status)

        return status, exc_msg + check_api_utils.state_markers[status], []

    def exception(self) -> Optional[Exception]:
        """Provides exceptions happened during last self.run() call or None"""
        return self._exception

    @classmethod
    def use_outdated_persisted_sections(cls) -> None:
        cls._use_outdated_persisted_sections = True

    @classmethod
    def set_use_outdated_cache_file(cls, state: bool = True) -> None:
        cls._use_outdated_cache_file = state
