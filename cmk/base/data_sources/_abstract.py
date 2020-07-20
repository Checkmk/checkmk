#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import json
import logging
import os
import sys
from typing import Any, cast, Dict, Final, Generic, Optional, Tuple, TypeVar, Union

import cmk.utils
import cmk.utils.debug
import cmk.utils.log  # TODO: Remove this!
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKSNMPError, MKTerminate, MKTimeout
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    RawAgentData,
    SectionName,
    ServiceCheckResult,
    SourceType,
)

import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.cpu_tracking as cpu_tracking
from cmk.base.check_utils import (
    BoundedAbstractPersistedSections,
    BoundedAbstractRawData,
    BoundedAbstractSectionContent,
    BoundedAbstractSections,
    PiggybackRawData,
    SectionCacheInfo,
)
from cmk.base.config import SelectedRawSections
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData, MKIPAddressLookupError

from ._cache import FileCache, SectionStore


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
        sections: BoundedAbstractSections,
        cache_info: SectionCacheInfo,
        piggybacked_raw_data: PiggybackRawData,
        persisted_sections: BoundedAbstractPersistedSections,
    ) -> None:
        super(ABCHostSections, self).__init__()
        self.sections = sections
        self.cache_info = cache_info
        self.piggybacked_raw_data = piggybacked_raw_data
        self.persisted_sections = persisted_sections

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

    @abc.abstractmethod
    def _extend_section(
        self,
        section_name: SectionName,
        section_content: BoundedAbstractSectionContent,
    ) -> None:
        raise NotImplementedError()

    def add_cached_section(
        self,
        section_name: SectionName,
        section: BoundedAbstractSectionContent,
        persisted_from: int,
        persisted_until: int,
    ) -> None:
        self.cache_info[section_name] = (persisted_from, persisted_until - persisted_from)
        # TODO: Find out why mypy complains about this
        self.sections[section_name] = section  # type: ignore[assignment]


BoundedAbstractHostSections = TypeVar("BoundedAbstractHostSections", bound=ABCHostSections)


class ABCConfigurator(abc.ABC):
    """Generate the configuration for the fetchers.

    Dump the JSON configuration from `configure_fetcher()`.

    """
    def __init__(self, *, description: str) -> None:
        self.description: Final[str] = description

    @abc.abstractmethod
    def configure_fetcher(self) -> Dict[str, Any]:
        raise NotImplementedError

    def configure_fetcher_json(self) -> str:
        return json.dumps(self.configure_fetcher())


class ABCDataSource(Generic[BoundedAbstractRawData, BoundedAbstractSections,
                            BoundedAbstractPersistedSections, BoundedAbstractHostSections],
                    metaclass=abc.ABCMeta):
    """Abstract base class for all data source classes"""

    source_type = SourceType.HOST

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
        hostname: HostName,
        ipaddress: Optional[HostAddress],
        *,
        id_: str,
        cpu_tracking_id: str,
    ) -> None:
        """Initialize the abstract base class

        :param hostname: The name of the host this data source is associated to
        :param ipaddress: The IP address of the host this data source is associated to
        """
        super(ABCDataSource, self).__init__()
        self.hostname: Final[HostName] = hostname
        self.ipaddress: Final[Optional[HostAddress]] = ipaddress
        self.id: Final[str] = id_
        self._cpu_tracking_id: Final[str] = cpu_tracking_id
        self._max_cachefile_age: Optional[int] = None

        self._logger = logging.getLogger("cmk.base.data_source.%s" % self.id)
        self._setup_logger()

        # Runtime data (managed by self.run()) - Meant for self.get_summary_result()
        self._exception: Optional[Exception] = None
        self._host_sections: Optional[BoundedAbstractHostSections] = None
        self._persisted_sections: Optional[BoundedAbstractPersistedSections] = None

        self._config_cache = config.get_config_cache()
        self._host_config = self._config_cache.get_host_config(self.hostname)

    def __repr__(self):
        return "%s(%r, %r)" % (
            type(self).__name__,
            self.hostname,
            self.ipaddress,
        )

    def _setup_logger(self) -> None:
        """Add the source log prefix to the class logger"""
        self._logger.propagate = False
        handler = logging.StreamHandler(stream=sys.stdout)
        fmt = " %s[%s%s%s]%s %%(message)s" % (tty.bold, tty.normal, self.id, tty.bold, tty.normal)
        handler.setFormatter(logging.Formatter(fmt))
        del self._logger.handlers[:]  # Remove all previously existing handlers
        self._logger.addHandler(handler)

    def run(self, *, selected_raw_sections: Optional[SelectedRawSections]) -> ABCHostSections:
        """
        :param selected_raw_section: A set of raw sections, that we
        are interested in.  If set, we assume that these sections should
        be produced if possible, and any raw section that is not listed
        here *may* be omitted.
        """
        result = self._run(selected_raw_sections=selected_raw_sections, get_raw_data=False)
        if not isinstance(result, ABCHostSections):
            raise TypeError("Got invalid type: %r" % result)
        return result

    def run_raw(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> RawAgentData:
        """Small wrapper for self._run() which always returns raw data source data

        Both hostname and ipaddress are optional, used for virtual
        Check_MK clusters."""
        result = self._run(selected_raw_sections=selected_raw_sections, get_raw_data=True)
        if not isinstance(result, RawAgentData):
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

        self._exception = None
        self._host_sections = None
        self._persisted_sections = None
        section_store = SectionStore(self._persisted_sections_file_path(), self._logger)

        try:
            persisted_sections_from_disk: BoundedAbstractPersistedSections = section_store.load(
                self._use_outdated_persisted_sections)
            self._persisted_sections = persisted_sections_from_disk

            raw_data, is_cached_data = self._get_raw_data(
                selected_raw_sections=selected_raw_sections)

            self._host_sections = host_sections = self._convert_to_sections(raw_data)
            assert isinstance(host_sections, ABCHostSections)

            if get_raw_data:
                return raw_data

            # Add information from previous persisted infos
            host_sections = self._update_info_with_persisted_sections(
                persisted_sections_from_disk,
                host_sections,
                is_cached_data,
                section_store,
            )
            self._persisted_sections = host_sections.persisted_sections

            return host_sections

        except MKTerminate:
            raise

        except Exception as e:
            self._logger.log(VERBOSE, "ERROR: %s", e)
            if cmk.utils.debug.enabled():
                raise
            self._exception = e

        if get_raw_data:
            return self._empty_raw_data()
        return self._empty_host_sections()

    def _make_file_cache(self) -> FileCache:
        return FileCache(
            self._cache_file_path(),
            self._max_cachefile_age,
            self.is_agent_cache_disabled(),
            self.get_may_use_cache_file(),
            self._use_outdated_cache_file,
            self._from_cache_file,
            self._to_cache_file,
            self._logger,
        )

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
        file_cache = self._make_file_cache()
        raw_data = file_cache.read()
        if raw_data:
            self._logger.log(VERBOSE, "Use cached data")
            return raw_data, True

        if raw_data is None and config.simulation_mode:
            raise MKAgentError("Got no data (Simulation mode enabled and no cachefile present)")

        self._logger.log(VERBOSE, "Execute data source")
        raw_data = self._execute(selected_raw_sections=selected_raw_sections)
        file_cache.write(raw_data)
        return raw_data, False

    @abc.abstractmethod
    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> BoundedAbstractRawData:
        """Fetches the current agent data from the source specified with
        hostname and ipaddress and returns the result as "raw data" that is
        later converted by self._convert_to_sections() to a HostSection().

        The "raw data" is the raw byte string returned by the source for
        AgentDataSource sources. The SNMPDataSource source already
        return the final data structure to be wrapped into HostSections()."""
        raise NotImplementedError()

    @abc.abstractmethod
    def _empty_raw_data(self) -> BoundedAbstractRawData:
        raise NotImplementedError()

    @abc.abstractmethod
    def _empty_host_sections(self) -> BoundedAbstractHostSections:
        raise NotImplementedError()

    @abc.abstractmethod
    def _from_cache_file(self, raw_data: bytes) -> BoundedAbstractRawData:
        raise NotImplementedError()

    @abc.abstractmethod
    def _to_cache_file(self, raw_data: BoundedAbstractRawData) -> bytes:
        raise NotImplementedError()

    @abc.abstractmethod
    def _convert_to_sections(
        self,
        raw_data: BoundedAbstractRawData,
    ) -> BoundedAbstractHostSections:
        """See _execute() for details"""
        raise NotImplementedError()

    def _cache_file_path(self) -> str:
        return os.path.join(self._cache_dir(), self.hostname)

    def _cache_dir(self) -> str:
        return os.path.join(cmk.utils.paths.data_source_cache_dir, self.id)

    def _persisted_sections_file_path(self) -> str:
        return os.path.join(self._persisted_sections_dir(), self.hostname)

    def _persisted_sections_dir(self) -> str:
        return os.path.join(cmk.utils.paths.var_dir, "persisted_sections", self.id)

    def name(self) -> str:
        """Return a unique (per host) textual identification of the data source

        This name is used to identify this data source instance compared to other
        instances of this data source type and also to instances of other data source
        types.

        It is only used during execution of Check_MK and not persisted. This means
        the algorithm can be changed at any time.
        """
        return ":".join([self.id, self.hostname, self.ipaddress or ""])

    @abc.abstractmethod
    def describe(self) -> str:
        """Return a short textual description of the datasource"""
        raise NotImplementedError()

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

    def get_summary_result_for_discovery(self) -> ServiceCheckResult:
        return self._get_summary_result(for_checking=False)

    def get_summary_result_for_inventory(self) -> ServiceCheckResult:
        return self._get_summary_result(for_checking=False)

    def get_summary_result_for_checking(self) -> ServiceCheckResult:
        return self._get_summary_result()

    def _get_summary_result(
        self,
        for_checking: bool = True,
    ) -> ServiceCheckResult:
        """Returns a three element tuple of state, output and perfdata (list) that summarizes
        the execution result of this data source.

        This is e.g. used for the output of the "Check_MK", "Check_MK Discovery" or
        "Check_MK HW/SW Inventory" services."""

        if not self._exception:
            return self._summary_result(for_checking)

        exc_msg = "%s" % self._exception

        if isinstance(self._exception, MKEmptyAgentData):
            status = self._host_config.exit_code_spec().get("empty_output", 2)

        elif isinstance(self._exception, (MKAgentError, MKIPAddressLookupError, MKSNMPError)):
            status = self._host_config.exit_code_spec().get("connection", 2)

        elif isinstance(self._exception, MKTimeout):
            status = self._host_config.exit_code_spec().get("timeout", 2)

        else:
            status = self._host_config.exit_code_spec().get("exception", 3)
        status = cast(int, status)

        return status, exc_msg + check_api_utils.state_markers[status], []

    @abc.abstractmethod
    def _summary_result(self, for_checking: bool) -> ServiceCheckResult:
        """Produce a source specific summary result in case no exception occured.

        When an exception occured while processing a data source, the generic
        self.get_summary_result() will handle this.

        The default is to return empty summary information, which will then be
        ignored by the code that processes the summary result."""
        raise NotImplementedError()

    def exception(self) -> Optional[Exception]:
        """Provides exceptions happened during last self.run() call or None"""
        return self._exception

    def _update_info_with_persisted_sections(
        self,
        persisted_sections: BoundedAbstractPersistedSections,
        host_sections: BoundedAbstractHostSections,
        is_cached_data: bool,
        section_store: SectionStore,
    ) -> BoundedAbstractHostSections:
        if host_sections.persisted_sections and not is_cached_data:
            persisted_sections.update(host_sections.persisted_sections)
            section_store.store(persisted_sections)

        if not persisted_sections:
            return host_sections

        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue  # Skip entries of "old" format

            persisted_from, persisted_until, section_info = entry

            # Don't overwrite sections that have been received from the source with this call
            if section_name in host_sections.sections:
                self._logger.debug("Skipping persisted section %r, live data available",
                                   section_name)
            else:
                self._logger.debug("Using persisted section %r", section_name)
                host_sections.add_cached_section(
                    section_name,
                    section_info,
                    persisted_from,
                    persisted_until,
                )
        return host_sections

    @classmethod
    def use_outdated_persisted_sections(cls) -> None:
        cls._use_outdated_persisted_sections = True

    @classmethod
    def set_use_outdated_cache_file(cls, state: bool = True) -> None:
        cls._use_outdated_cache_file = state
