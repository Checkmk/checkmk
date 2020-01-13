#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import errno
import os
import socket
import time
import abc
import logging
import sys
from typing import AnyStr, Dict, Set, List, cast, Tuple, Union, Optional, Text  # pylint: disable=unused-import
import six

import cmk.utils.log  # TODO: Remove this!
from cmk.utils.log import VERBOSE

import cmk.utils
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.misc
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.utils.encoding import (
    convert_to_unicode,
    ensure_bytestr,
)

import cmk.base.utils
import cmk.base.agent_simulator
import cmk.base.console as console
import cmk.base.config as config
import cmk.base.cpu_tracking as cpu_tracking
import cmk.base.ip_lookup as ip_lookup
import cmk.base.check_api_utils as check_api_utils
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData, MKSNMPError, \
                                MKIPAddressLookupError
from cmk.base.check_api_utils import state_markers
from cmk.base.check_utils import (  # pylint: disable=unused-import
    PersistedSections, SectionName, SectionContent, ServiceState, ServiceDetails,
    ServiceCheckResult, Metric, CheckPluginName, AgentSections, PiggybackRawData,
    AgentSectionCacheInfo,
)
from cmk.base.utils import HostName, HostAddress, RawAgentData  # pylint: disable=unused-import

from .host_sections import HostSections


class DataSource(six.with_metaclass(abc.ABCMeta, object)):
    """Abstract base class for all data source classes"""

    _for_mgmt_board = False

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

    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(DataSource, self).__init__()
        self._hostname = hostname
        self._ipaddress = ipaddress
        self._max_cachefile_age = None  # type: Optional[int]
        self._enforced_check_plugin_names = None  # type: Optional[Set[CheckPluginName]]

        self._logger = console.logger.getChild("data_source.%s" % self.id())
        self._setup_logger()

        # Runtime data (managed by self.run()) - Meant for self.get_summary_result()
        self._exception = None  # type: Optional[Exception]
        self._host_sections = None  # type: Optional[HostSections]
        self._persisted_sections = None  # type: Optional[PersistedSections]

        self._config_cache = config.get_config_cache()
        self._host_config = self._config_cache.get_host_config(self._hostname)

    def _setup_logger(self):
        # type: () -> None
        """Add the source log prefix to the class logger"""
        self._logger.propagate = False
        handler = logging.StreamHandler(stream=sys.stdout)
        fmt = " %s[%s%s%s]%s %%(message)s" % (tty.bold, tty.normal, self.id(), tty.bold, tty.normal)
        handler.setFormatter(logging.Formatter(fmt))
        del self._logger.handlers[:]  # Remove all previously existing handlers
        self._logger.addHandler(handler)

    def run(self, hostname=None, ipaddress=None):
        # type: (Optional[HostName], Optional[HostAddress]) -> HostSections
        result = self._run(hostname, ipaddress, get_raw_data=False)
        if not isinstance(result, HostSections):
            raise TypeError("Got invalid type: %r" % result)
        return result

    def run_raw(self, hostname=None, ipaddress=None):
        # type: (Optional[HostName], Optional[HostAddress]) -> RawAgentData
        """Small wrapper for self._run() which always returns raw data source data

        Both hostname and ipaddress are optional, used for virtual
        Check_MK clusters."""
        result = self._run(hostname, ipaddress, get_raw_data=True)
        if not isinstance(result, RawAgentData):
            raise TypeError("Got invalid type: %r" % result)
        return result

    def _run(self, hostname, ipaddress, get_raw_data):
        # type: (Optional[HostName], Optional[HostAddress], bool) -> Union[RawAgentData, HostSections]
        """Wrapper for self._execute() that unifies several things:

        a) Exception handling
        b) Caching of raw data
        c) CPU tracking

        Exceptions: All exceptions are caught and written to self._exception. The caller
        should use self.get_summary_result() to get the summary result of this data source
        which also includes information about the happed exception. In case the --debug
        mode is enabled, the exceptions are raised. self._exception is re-initialized
        to None when this method is called.

        Both hostname and ipaddress are optional, used for virtual
        Check_MK clusters."""

        # TODO: This is manipulating the state that has been initialized with the constructor?!
        if hostname is not None:
            self._hostname = hostname
        if ipaddress is not None:
            self._ipaddress = ipaddress

        self._exception = None
        self._host_sections = None
        self._persisted_sections = None

        try:
            cpu_tracking.push_phase(self._cpu_tracking_id())

            persisted_sections_from_disk = self._load_persisted_sections()
            self._persisted_sections = persisted_sections_from_disk

            raw_data, is_cached_data = self._get_raw_data()

            self._host_sections = host_sections = self._convert_to_sections(raw_data)
            assert isinstance(host_sections, HostSections)

            if get_raw_data:
                return raw_data

            # Add information from previous persisted infos
            host_sections = self._update_info_with_persisted_sections(persisted_sections_from_disk,
                                                                      host_sections, is_cached_data)
            self._persisted_sections = host_sections.persisted_sections

            return host_sections

        except MKTerminate:
            raise

        except Exception as e:
            self._logger.log(VERBOSE, "ERROR: %s", e)
            if cmk.utils.debug.enabled():
                raise
            self._exception = e
        finally:
            cpu_tracking.pop_phase()

        if get_raw_data:
            return ""
        return HostSections()

    def _get_raw_data(self):
        # type: () -> Tuple[RawAgentData, bool]
        """Returns the current raw data of this data source

        It either uses previously cached raw data of this data source or
        executes the data source to get new data.

        The "raw data" is the raw byte string returned by the source for
        CheckMKAgentDataSource sources. The SNMPDataSource source already
        return the final info data structure.
        """
        raw_data = self._read_cache_file()
        if raw_data:
            self._logger.log(VERBOSE, "Use cached data")
            return raw_data, True

        elif raw_data is None and config.simulation_mode:
            raise MKAgentError("Got no data (Simulation mode enabled and no cachefile present)")

        self._logger.log(VERBOSE, "Execute data source")
        raw_data = self._execute()
        self._write_cache_file(raw_data)
        return raw_data, False

    @abc.abstractmethod
    def _execute(self):
        # type: () -> RawAgentData
        """Fetches the current agent data from the source specified with
        hostname and ipaddress and returns the result as "raw data" that is
        later converted by self._convert_to_sections() to a HostSection().

        The "raw data" is the raw byte string returned by the source for
        CheckMKAgentDataSource sources. The SNMPDataSource source already
        return the final data structure to be wrapped into HostSections()."""
        raise NotImplementedError()

    def _read_cache_file(self):
        # type: () -> Optional[RawAgentData]
        assert self._max_cachefile_age is not None

        cachefile = self._cache_file_path()

        if not os.path.exists(cachefile):
            self._logger.debug("Not using cache (Does not exist)")
            return None

        if self.is_agent_cache_disabled():
            self._logger.debug("Not using cache (Cache usage disabled)")
            return None

        if not self._may_use_cache_file and not config.simulation_mode:
            self._logger.debug("Not using cache (Don't try it)")
            return None

        may_use_outdated = config.simulation_mode or self._use_outdated_cache_file
        cachefile_age = cmk.utils.cachefile_age(cachefile)
        if not may_use_outdated and cachefile_age > self._max_cachefile_age:
            self._logger.debug("Not using cache (Too old. Age is %d sec, allowed is %s sec)" %
                               (cachefile_age, self._max_cachefile_age))
            return None

        # TODO: Use some generic store file read function to generalize error handling,
        # but there is currently no function that simply reads data from the file
        result = open(cachefile).read()
        if not result:
            self._logger.debug("Not using cache (Empty)")
            return None

        self._logger.log(VERBOSE, "Using data from cache file %s", cachefile)
        return self._from_cache_file(result)

    def _write_cache_file(self, raw_data):
        # type: (RawAgentData) -> None
        if self.is_agent_cache_disabled():
            self._logger.debug("Not writing data to cache file (Cache usage disabled)")
            return

        cachefile = self._cache_file_path()

        try:
            try:
                os.makedirs(os.path.dirname(cachefile))
            except OSError as e:
                if e.errno == errno.EEXIST:
                    pass
                else:
                    raise
        except Exception as e:
            raise MKGeneralException("Cannot create directory %r: %s" %
                                     (os.path.dirname(cachefile), e))

        self._logger.debug("Write data to cache file %s" % (cachefile))
        try:
            store.save_file(cachefile, self._to_cache_file(raw_data))
        except Exception as e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (cachefile, e))

    def _from_cache_file(self, raw_data):
        # type: (RawAgentData) -> RawAgentData
        return raw_data

    def _to_cache_file(self, raw_data):
        # type: (RawAgentData) -> RawAgentData
        # TODO: This does not seem to be needed
        return ensure_bytestr(raw_data)

    @abc.abstractmethod
    def _convert_to_sections(self, raw_data):
        # type: (RawAgentData) -> HostSections
        """See _execute() for details"""
        raise NotImplementedError()

    def _cache_file_path(self):
        # type: () -> str
        return os.path.join(self._cache_dir(), self._hostname)

    def _cache_dir(self):
        # type: () -> str
        return os.path.join(cmk.utils.paths.data_source_cache_dir, self.id())

    def _persisted_sections_file_path(self):
        # type: () -> str
        return _persisted_sections_file_path(self._persisted_sections_dir(), self._hostname)

    def _persisted_sections_dir(self):
        # type: () -> str
        return _persisted_sections_dir(self.id())

    def get_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        if self._enforced_check_plugin_names is not None:
            return self._enforced_check_plugin_names
        return self._gather_check_plugin_names()

    @abc.abstractmethod
    def _gather_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        """
        Returns a collection of check plugin names which are supported by
        the device.

        Example: SNMP scan
        """
        raise NotImplementedError()

    def enforce_check_plugin_names(self, check_plugin_names):
        # type: (Set[CheckPluginName]) -> None
        """
        Returns a subset of beforehand gathered check plugin names which are
        supported by the data source.

        Example: management board checks only for management board data sources
        """
        if check_plugin_names is not None:
            self._enforced_check_plugin_names = config.filter_by_management_board(
                self._hostname, check_plugin_names, self._for_mgmt_board)
        else:
            self._enforced_check_plugin_names = check_plugin_names

    @abc.abstractmethod
    def _cpu_tracking_id(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractmethod
    def id(self):
        # type: () -> str
        """Return a unique identifier for this data source type
        It is used to identify the different data source types."""
        raise NotImplementedError()

    def name(self):
        # type: () -> str
        """Return a unique (per host) textual identification of the data source

        This name is used to identify this data source instance compared to other
        instances of this data source type and also to instances of other data source
        types.

        It is only used during execution of Check_MK and not persisted. This means
        the algorithm can be changed at any time.
        """
        return ":".join([self.id(), self._hostname, self._ipaddress or ""])

    @abc.abstractmethod
    def describe(self):
        # type: () -> str
        """Return a short textual description of the datasource"""
        raise NotImplementedError()

    def _verify_ipaddress(self):
        # type: () -> None
        if not self._ipaddress:
            raise MKIPAddressLookupError("Host as no IP address configured.")

        if self._ipaddress in ["0.0.0.0", "::"]:
            raise MKIPAddressLookupError(
                "Failed to lookup IP address and no explicit IP address configured")

    def set_max_cachefile_age(self, max_cachefile_age):
        # type: (int) -> None
        self._max_cachefile_age = max_cachefile_age

    @classmethod
    def disable_data_source_cache(cls):
        # type: () -> None
        cls._no_cache = True

    @classmethod
    def is_agent_cache_disabled(cls):
        # type: () -> bool
        return cls._no_cache

    @classmethod
    def get_may_use_cache_file(cls):
        # type: () -> bool
        return cls._may_use_cache_file

    @classmethod
    def set_may_use_cache_file(cls, state=True):
        # type: (bool) -> None
        cls._may_use_cache_file = state

    # TODO: Refactor the returned data of this method and self._summary_result()
    # to some wrapped object like CheckResult(...)
    def get_summary_result_for_discovery(self):
        # type: () -> ServiceCheckResult
        return self._get_summary_result(for_checking=False)

    def get_summary_result_for_inventory(self):
        # type: () -> ServiceCheckResult
        return self._get_summary_result(for_checking=False)

    def get_summary_result_for_checking(self):
        # type: () -> ServiceCheckResult
        return self._get_summary_result()

    def _get_summary_result(self, for_checking=True):
        # type: (bool) -> ServiceCheckResult
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

    def _summary_result(self, for_checking):
        # type: (bool) -> ServiceCheckResult
        """Produce a source specific summary result in case no exception occured.

        When an exception occured while processing a data source, the generic
        self.get_summary_result() will handle this.

        The default is to return empty summary information, which will then be
        ignored by the code that processes the summary result."""
        return 0, "Success", []

    def exception(self):
        # type: () -> Optional[Exception]
        """Provides exceptions happened during last self.run() call or None"""
        return self._exception

    #.
    #   .--PersistedCache------------------------------------------------------.
    #   |  ____               _     _           _  ____           _            |
    #   | |  _ \ ___ _ __ ___(_)___| |_ ___  __| |/ ___|__ _  ___| |__   ___   |
    #   | | |_) / _ \ '__/ __| / __| __/ _ \/ _` | |   / _` |/ __| '_ \ / _ \  |
    #   | |  __/  __/ |  \__ \ \__ \ ||  __/ (_| | |__| (_| | (__| | | |  __/  |
    #   | |_|   \___|_|  |___/_|___/\__\___|\__,_|\____\__,_|\___|_| |_|\___|  |
    #   |                                                                      |
    #   +----------------------------------------------------------------------+
    #   | Caching of info for multiple executions of Check_MK. Mostly caching  |
    #   | of sections that are not provided on each query.                     |
    #   '----------------------------------------------------------------------'

    def _store_persisted_sections(self, persisted_sections):
        # type: (PersistedSections) -> None
        if not persisted_sections:
            return

        file_path = self._persisted_sections_file_path()
        try:
            os.makedirs(os.path.dirname(file_path))
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        store.save_object_to_file(file_path, persisted_sections, pretty=False)
        self._logger.debug("Stored persisted sections: %s" % (", ".join(persisted_sections.keys())))

    def _update_info_with_persisted_sections(self, persisted_sections_from_disk, host_sections,
                                             is_cached_data):
        # type: (PersistedSections, HostSections, bool) -> HostSections
        persisted_sections = persisted_sections_from_disk
        persisted_sections_from_raw = host_sections.persisted_sections

        if persisted_sections_from_raw and not is_cached_data:
            persisted_sections.update(persisted_sections_from_raw)
            self._store_persisted_sections(persisted_sections)

        if not persisted_sections:
            return host_sections

        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue  # Skip entries of "old" format

            persisted_from, persisted_until, section_info = entry

            # Don't overwrite sections that have been received from the source with this call
            if section_name in host_sections.sections:
                self._logger.debug("Skipping persisted section %r, live data available" %
                                   (section_name))
            else:
                self._logger.debug("Using persisted section %r" % (section_name))
                host_sections.add_cached_section(section_name, section_info, persisted_from,
                                                 persisted_until)
        return host_sections

    def _load_persisted_sections(self):
        # type: () -> PersistedSections
        file_path = self._persisted_sections_file_path()

        persisted_sections = store.load_object_from_file(file_path, default={})
        filtered_persisted_sections = self._filter_outdated_persisted_sections(persisted_sections)

        if not filtered_persisted_sections:
            self._logger.debug("No persisted sections loaded")
            try:
                os.remove(self._persisted_sections_file_path())
            except OSError:
                pass

        return filtered_persisted_sections

    # TODO: This is not race condition free when modifying the data. Either remove
    # the possible write here and simply ignore the outdated sections or lock when
    # reading and unlock after writing
    def _filter_outdated_persisted_sections(self, persisted_sections):
        # type: (PersistedSections) -> PersistedSections
        filtered_persisted_sections = {}
        now = time.time()
        for section_name, entry in persisted_sections.iteritems():
            if len(entry) == 2:
                persisted_until = entry[0]
            else:
                persisted_until = entry[1]

            if not self._use_outdated_persisted_sections and now > persisted_until:
                self._logger.debug("Persisted section %s is outdated by %d seconds. Skipping it." %
                                   (section_name, now - persisted_until))
                continue
            filtered_persisted_sections[section_name] = entry
        return filtered_persisted_sections

    @classmethod
    def use_outdated_persisted_sections(cls):
        # type: () -> None
        cls._use_outdated_persisted_sections = True

    @classmethod
    def set_use_outdated_cache_file(cls, state=True):
        # type: (bool) -> None
        cls._use_outdated_cache_file = state


class CheckMKAgentDataSource(six.with_metaclass(abc.ABCMeta, DataSource)):
    """Abstract base class for all data sources that work with the Check_MK agent data format"""

    # NOTE: This class is obviously still abstract, but pylint fails to see
    # this, even in the presence of the meta class assignment below, see
    # https://github.com/PyCQA/pylint/issues/179.

    # pylint: disable=abstract-method

    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(CheckMKAgentDataSource, self).__init__(hostname, ipaddress)
        self._is_main_agent_data_source = False

    # TODO: We should cleanup these old directories one day. Then we can remove this special case
    def set_main_agent_data_source(self):
        # type: () -> None
        """Tell the data source that it's the main agent based data source

        The data source that is the "main" agent based data source uses the
        cache and persisted directories that existed before the data source
        concept has been added where each data source has it's own set of
        directories.
        """
        self._is_main_agent_data_source = True

    def _gather_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        return config.discoverable_tcp_checks()

    def _cpu_tracking_id(self):
        # type: () -> str
        return "agent"

    def _cache_dir(self):
        # The main agent has another cache directory to be compatible with older Check_MK
        if self._is_main_agent_data_source:
            return cmk.utils.paths.tcp_cache_dir

        return super(CheckMKAgentDataSource, self)._cache_dir()

    def _persisted_sections_dir(self):
        # The main agent has another cache directory to be compatible with older Check_MK
        if self._is_main_agent_data_source:
            return os.path.join(cmk.utils.paths.var_dir, "persisted")

        return super(CheckMKAgentDataSource, self)._persisted_sections_dir()

    def _convert_to_sections(self, raw_data):
        if config.agent_simulator:
            raw_data = cmk.base.agent_simulator.process(raw_data)

        return self._parse_info(raw_data.split("\n"))

    def _parse_info(self, lines):
        # type: (List[bytes]) -> HostSections
        """Split agent output in chunks, splits lines by whitespaces.

        Returns a HostSections() object.
        """
        sections = {}  # type: AgentSections
        # Unparsed info for other hosts. A dictionary, indexed by the piggybacked host name.
        # The value is a list of lines which were received for this host.
        piggybacked_raw_data = {}  # type: PiggybackRawData
        piggybacked_hostname = None
        piggybacked_cached_at = int(time.time())
        # Transform to seconds and give the piggybacked host a little bit more time
        piggybacked_cache_age = int(1.5 * 60 * self._host_config.check_mk_check_interval)

        # handle sections with option persist(...)
        persisted_sections = {}  # type: PersistedSections
        section_content = []  # type: SectionContent
        section_options = {}  # type: Dict[str, Optional[str]]
        agent_cache_info = {}  # type: AgentSectionCacheInfo
        separator = None  # type: Optional[str]
        encoding = None
        for line in lines:
            line = line.rstrip("\r")
            stripped_line = line.strip()
            if stripped_line[:4] == '<<<<' and stripped_line[-4:] == '>>>>':
                piggybacked_hostname =\
                    self._get_sanitized_and_translated_piggybacked_hostname(stripped_line)

            elif piggybacked_hostname:  # processing data for an other host
                if stripped_line[:3] == '<<<' and stripped_line[-3:] == '>>>':
                    line = self._add_cached_info_to_piggybacked_section_header(
                        stripped_line, piggybacked_cached_at, piggybacked_cache_age)
                piggybacked_raw_data.setdefault(piggybacked_hostname, []).append(line)

            # Found normal section header
            # section header has format <<<name:opt1(args):opt2:opt3(args)>>>
            elif stripped_line[:3] == '<<<' and stripped_line[-3:] == '>>>':
                section_header = stripped_line[3:-3]
                headerparts = section_header.split(":")
                section_name = headerparts[0]
                section_options = {}
                opt_args = None  # type: Optional[str]
                for o in headerparts[1:]:
                    opt_parts = o.split("(")
                    opt_name = opt_parts[0]
                    if len(opt_parts) > 1:
                        opt_args = opt_parts[1][:-1]
                    else:
                        opt_args = None
                    section_options[opt_name] = opt_args

                content = sections.get(section_name, None)
                if content is None:  # section appears in output for the first time
                    section_content = []
                    sections[section_name] = section_content
                else:
                    section_content = content

                try:
                    separator = chr(int(cast(str, section_options["sep"])))
                except Exception:
                    separator = None

                # Split of persisted section for server-side caching
                if "persist" in section_options:
                    until = int(cast(str, section_options["persist"]))
                    cached_at = int(time.time())  # Estimate age of the data
                    cache_interval = int(until - cached_at)
                    agent_cache_info[section_name] = (cached_at, cache_interval)
                    persisted_sections[section_name] = (cached_at, until, section_content)

                if "cached" in section_options:
                    cache_times = map(int, cast(str, section_options["cached"]).split(","))
                    agent_cache_info[section_name] = cache_times[0], cache_times[1]

                # The section data might have a different encoding
                encoding = section_options.get("encoding")

            elif stripped_line != '':
                if "nostrip" not in section_options:
                    line = stripped_line

                if encoding:
                    decoded_line = convert_to_unicode(line, std_encoding=encoding)
                else:
                    decoded_line = convert_to_unicode(line)

                section_content.append(decoded_line.split(separator))

        return HostSections(sections, agent_cache_info, piggybacked_raw_data, persisted_sections)

    def _get_sanitized_and_translated_piggybacked_hostname(self, orig_piggyback_header):
        # type: (str) -> Optional[HostName]
        piggybacked_hostname = orig_piggyback_header[4:-4]
        if not piggybacked_hostname:
            return None

        piggybacked_hostname = config.translate_piggyback_host(self._hostname, piggybacked_hostname)
        if piggybacked_hostname == self._hostname or not piggybacked_hostname:
            return None  # unpiggybacked "normal" host

        # Protect Check_MK against unallowed host names. Normally source scripts
        # like agent plugins should care about cleaning their provided host names
        # up, but we need to be sure here to prevent bugs in Check_MK code.
        # a) Replace spaces by underscores
        return piggybacked_hostname.replace(" ", "_")

    def _add_cached_info_to_piggybacked_section_header(self, orig_section_header, cached_at,
                                                       cache_age):
        # type: (str, int, int) -> str
        if ':cached(' in orig_section_header or ':persist(' in orig_section_header:
            return orig_section_header
        return '<<<%s:cached(%s,%s)>>>' % (orig_section_header[3:-3], cached_at, cache_age)

    # TODO: refactor
    def _summary_result(self, for_checking):
        # type: (bool) -> ServiceCheckResult
        assert isinstance(self._host_sections, HostSections)

        cmk_section = self._host_sections.sections.get("check_mk")
        agent_info = self._get_agent_info(cmk_section)
        agent_version = agent_info["version"]

        status = 0  # type: ServiceState
        output = []  # type: List[ServiceDetails]
        perfdata = []  # type: List[Metric]
        if not self._host_config.is_cluster and agent_version is not None:
            output.append("Version: %s" % agent_version)

        if not self._host_config.is_cluster and agent_info["agentos"] is not None:
            output.append("OS: %s" % agent_info["agentos"])

        if for_checking and cmk_section:
            for sub_result in [
                    self._sub_result_version(agent_info),
                    self._sub_result_only_from(agent_info),
            ]:
                if not sub_result:
                    continue
                sub_status, sub_output, sub_perfdata = sub_result
                status = max(status, sub_status)
                output.append(sub_output)
                perfdata += sub_perfdata
        return status, ", ".join(output), perfdata

    def _get_agent_info(self, cmk_section):
        agent_info = {
            "version": u"unknown",
            "agentos": u"unknown",
        }

        if self._host_sections is None or not cmk_section:
            return agent_info

        for line in cmk_section:
            value = " ".join(line[1:]) if len(line) > 1 else None
            agent_info[line[0][:-1].lower()] = value
        return agent_info

    def _sub_result_version(self, agent_info):
        # type: (Dict[str, Text]) -> Optional[ServiceCheckResult]
        agent_version = cast(str, agent_info["version"])
        expected_version = self._host_config.agent_target_version

        if expected_version and agent_version \
             and not self._is_expected_agent_version(agent_version, expected_version):
            expected = u""
            # expected version can either be:
            # a) a single version string
            # b) a tuple of ("at_least", {'daily_build': '2014.06.01', 'release': '1.2.5i4'}
            #    (the dict keys are optional)
            if isinstance(expected_version, tuple) and expected_version[0] == 'at_least':
                spec = cast(Dict[str, str], expected_version[1])
                expected = 'at least'
                if 'daily_build' in spec:
                    expected += ' build %s' % spec['daily_build']
                if 'release' in spec:
                    if 'daily_build' in spec:
                        expected += ' or'
                    expected += ' release %s' % spec['release']
            else:
                expected = "%s" % (expected_version,)
            status = cast(int, self._host_config.exit_code_spec().get("wrong_version", 1))
            return (status, "unexpected agent version %s (should be %s)%s" %
                    (agent_version, expected, state_markers[status]), [])

        elif config.agent_min_version and cast(int, agent_version) < config.agent_min_version:
            # TODO: This branch seems to be wrong. Or: In which case is agent_version numeric?
            status = cast(int, self._host_config.exit_code_spec().get("wrong_version", 1))
            return (status, "old plugin version %s (should be at least %s)%s" %
                    (agent_version, config.agent_min_version, state_markers[status]), [])

        return None

    def _sub_result_only_from(self, agent_info):
        # type: (Dict[str, Text]) -> Optional[ServiceCheckResult]
        agent_only_from = agent_info.get("onlyfrom")
        if agent_only_from is None:
            return None

        config_only_from = self._host_config.only_from
        if config_only_from is None:
            return None

        allowed_nets = set(_normalize_ip_addresses(agent_only_from))
        expected_nets = set(_normalize_ip_addresses(config_only_from))
        if allowed_nets == expected_nets:
            return 0, "Allowed IP ranges: %s%s" % (" ".join(allowed_nets), state_markers[0]), []

        infotexts = []
        exceeding = allowed_nets - expected_nets
        if exceeding:
            infotexts.append("exceeding: %s" % " ".join(sorted(exceeding)))
        missing = expected_nets - allowed_nets
        if missing:
            infotexts.append("missing: %s" % " ".join(sorted(missing)))

        return 1, "Unexpected allowed IP ranges (%s)%s" % (", ".join(infotexts),
                                                           state_markers[1]), []

    def _is_expected_agent_version(self, agent_version, expected_version):
        # type: (Optional[str], config.AgentTargetVersion) -> bool
        try:
            if agent_version is None:
                return False

            if agent_version in ['(unknown)', 'None']:
                return False

            if isinstance(expected_version, six.string_types) and expected_version != agent_version:
                return False

            elif isinstance(expected_version, tuple) and expected_version[0] == 'at_least':
                spec = cast(Dict[str, str], expected_version[1])
                if cmk.utils.misc.is_daily_build_version(agent_version) and 'daily_build' in spec:
                    expected = int(spec['daily_build'].replace('.', ''))

                    branch = cmk.utils.misc.branch_of_daily_build(agent_version)
                    if branch == "master":
                        agent = int(agent_version.replace('.', ''))

                    else:  # branch build (e.g. 1.2.4-2014.06.01)
                        agent = int(agent_version.split('-')[1].replace('.', ''))

                    if agent < expected:
                        return False

                elif 'release' in spec:
                    if cmk.utils.misc.is_daily_build_version(agent_version):
                        return False

                    if cmk.utils.werks.parse_check_mk_version(agent_version) \
                        < cmk.utils.werks.parse_check_mk_version(spec['release']):
                        return False

            return True
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKGeneralException(
                "Unable to check agent version (Agent: %s Expected: %s, Error: %s)" %
                (agent_version, expected_version, e))


class ManagementBoardDataSource(six.with_metaclass(abc.ABCMeta, DataSource)):
    """Abstract base class for all data sources that work with the management board configuration"""

    # NOTE: This class is obviously still abstract, but pylint fails to see
    # this, even in the presence of the meta class assignment below, see
    # https://github.com/PyCQA/pylint/issues/179.

    # pylint: disable=abstract-method

    _for_mgmt_board = True

    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(ManagementBoardDataSource, self).__init__(hostname, ipaddress)
        # Do not use the (custom) ipaddress for the host. Use the management board
        # address instead
        self._ipaddress = self._management_board_ipaddress(hostname)
        self._credentials = self._host_config.management_credentials

    def _management_board_ipaddress(self, hostname):
        # type: (HostName) -> Optional[HostAddress]
        mgmt_ipaddress = self._host_config.management_address

        if mgmt_ipaddress is None:
            return None

        if not self._is_ipaddress(mgmt_ipaddress):
            try:
                return ip_lookup.lookup_ip_address(mgmt_ipaddress)
            except MKIPAddressLookupError:
                return None
        else:
            return mgmt_ipaddress

    # TODO: Why is it used only here?
    @staticmethod
    def _is_ipaddress(address):
        # type: (HostAddress) -> bool
        if address is None:
            return False

        try:
            socket.inet_pton(socket.AF_INET, address)
            return True
        except socket.error:
            # not a ipv4 address
            pass

        try:
            socket.inet_pton(socket.AF_INET6, address)
            return True
        except socket.error:
            # no ipv6 address either
            return False


def has_persisted_agent_sections(datasource_id, hostname):
    # type: (str, str) -> bool
    return os.path.exists(_persisted_sections_file_path(datasource_id, hostname))


def _persisted_sections_file_path(datasource_id, hostname):
    # type: (str, str) -> str
    return os.path.join(_persisted_sections_dir(datasource_id), hostname)


def _persisted_sections_dir(datasource_id):
    # type: (str) -> str
    return os.path.join(cmk.utils.paths.var_dir, "persisted_sections", datasource_id)


def _normalize_ip_addresses(ip_addresses):
    # type: (Union[AnyStr, List[AnyStr]]) -> List[AnyStr]
    '''factorize 10.0.0.{1,2,3}'''
    if not isinstance(ip_addresses, list):
        ip_addresses = ip_addresses.split()

    expanded = [word for word in ip_addresses if '{' not in word]
    for word in ip_addresses:
        if word in expanded:
            continue
        try:
            prefix, tmp = word.split('{')
            curly, suffix = tmp.split('}')
            expanded.extend(prefix + i + suffix for i in curly.split(','))
        except:
            raise MKGeneralException("could not expand %r" % word)
    return expanded
