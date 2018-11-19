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

import os
import socket
import time
import abc

import cmk.log

import cmk.debug
import cmk.paths
import cmk.store as store
import cmk.tty as tty
import cmk.cpu_tracking as cpu_tracking
from cmk.exceptions import MKGeneralException, MKTerminate, MKTimeout

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.ip_lookup as ip_lookup
import cmk_base.check_api_utils as check_api_utils
from cmk_base.exceptions import MKAgentError, MKEmptyAgentData, MKSNMPError, \
                                MKIPAddressLookupError

from .host_sections import HostSections


class DataSource(object):
    """Abstract base class for all data source classes"""
    __metaclass__ = abc.ABCMeta

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
        super(DataSource, self).__init__()
        self._hostname = hostname
        self._ipaddress = ipaddress
        self._max_cachefile_age = None
        self._enforced_check_plugin_names = None

        self._logger = console.logger.getChild("data_source.%s" % self.id())
        self._setup_logger()

        # Runtime data (managed by self.run()) - Meant for self.get_summary_result()
        self._exception = None
        self._host_sections = None
        self._exit_code_spec = config.exit_code_spec(hostname, data_source_id=self.id())

    def _setup_logger(self):
        """Add the source log prefix to the class logger"""
        self._logger.propagate = False
        self._logger.set_format(
            " %s[%s%s%s]%s %%(message)s" % (tty.bold, tty.normal, self.id(), tty.bold, tty.normal))

    def run(self, hostname=None, ipaddress=None, get_raw_data=False):
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

        if hostname is not None:
            self._hostname = hostname
        if ipaddress is not None:
            self._ipaddress = ipaddress

        self._exception = None
        self._host_sections = None

        try:
            cpu_tracking.push_phase(self._cpu_tracking_id())

            raw_data, is_cached_data = self._get_raw_data()

            self._host_sections = host_sections = self._convert_to_sections(raw_data)
            assert isinstance(host_sections, HostSections)

            if get_raw_data:
                return raw_data

            if host_sections.persisted_sections and not is_cached_data:
                self._store_persisted_sections(host_sections.persisted_sections)

            # Add information from previous persisted infos
            host_sections = self._update_info_with_persisted_sections(host_sections)

            return host_sections

        except MKTerminate:
            raise

        except Exception, e:
            self._logger.verbose("ERROR: %s" % e)
            if cmk.debug.enabled():
                raise
            self._exception = e
        finally:
            cpu_tracking.pop_phase()

        if get_raw_data:
            return ""
        return HostSections()

    def _get_raw_data(self):
        """Returns the current raw data of this data source

        It either uses previously cached raw data of this data source or
        executes the data source to get new data.

        The "raw data" is the raw byte string returned by the source for
        CheckMKAgentDataSource sources. The SNMPDataSource source already
        return the final info data structure.
        """
        raw_data = self._read_cache_file()
        if raw_data:
            self._logger.verbose("Use cached data")
            return raw_data, True

        elif raw_data is None and config.simulation_mode:
            raise MKAgentError("Got no data (Simulation mode enabled and no cachefile present)")

        self._logger.verbose("Execute data source")
        raw_data = self._execute()
        self._write_cache_file(raw_data)
        return raw_data, False

    def run_raw(self):
        """Small wrapper for self.run() which always returns raw data source data"""
        return self.run(get_raw_data=True)

    @abc.abstractmethod
    def _execute(self):
        """Fetches the current agent data from the source specified with
        hostname and ipaddress and returns the result as "raw data" that is
        later converted by self._convert_to_sections() to a HostSection().

        The "raw data" is the raw byte string returned by the source for
        CheckMKAgentDataSource sources. The SNMPDataSource source already
        return the final data structure to be wrapped into HostSections()."""
        raise NotImplementedError()

    def _read_cache_file(self):
        assert self._max_cachefile_age is not None

        cachefile = self._cache_file_path()

        if not os.path.exists(cachefile):
            self._logger.debug("Not using cache (Does not exist)")
            return

        if self.is_agent_cache_disabled():
            self._logger.debug("Not using cache (Cache usage disabled)")
            return

        if not self._may_use_cache_file and not config.simulation_mode:
            self._logger.debug("Not using cache (Don't try it)")
            return

        may_use_outdated = config.simulation_mode or self._use_outdated_cache_file
        if not may_use_outdated and cmk_base.utils.cachefile_age(
                cachefile) > self._max_cachefile_age:
            self._logger.debug("Not using cache (Too old. Age is %d sec, allowed is %s sec)" %
                               (cmk_base.utils.cachefile_age(cachefile), self._max_cachefile_age))
            return

        # TODO: Use some generic store file read function to generalize error handling,
        # but there is currently no function that simply reads data from the file
        result = open(cachefile).read()
        if not result:
            self._logger.debug("Not using cache (Empty)")
            return

        self._logger.verbose("Using data from cache file %s" % (cachefile))
        return self._from_cache_file(result)

    def _write_cache_file(self, raw_data):
        if self.is_agent_cache_disabled():
            self._logger.debug("Not writing data to cache file (Cache usage disabled)")
            return

        cachefile = self._cache_file_path()

        try:
            try:
                os.makedirs(os.path.dirname(cachefile))
            except OSError, e:
                if e.errno == 17:  # File exists
                    pass
                else:
                    raise
        except Exception, e:
            raise MKGeneralException(
                "Cannot create directory %r: %s" % (os.path.dirname(cachefile), e))

        self._logger.debug("Write data to cache file %s" % (cachefile))
        try:
            store.save_file(cachefile, self._to_cache_file(raw_data))
        except Exception, e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (cachefile, e))

    def _from_cache_file(self, raw_data):
        return raw_data

    def _to_cache_file(self, raw_data):
        return raw_data

    @abc.abstractmethod
    def _convert_to_sections(self, raw_data):
        """See _execute() for details"""
        raise NotImplementedError()

    def _cache_file_path(self):
        return os.path.join(self._cache_dir(), self._hostname)

    def _cache_dir(self):
        return os.path.join(cmk.paths.data_source_cache_dir, self.id())

    def _persisted_sections_file_path(self):
        return os.path.join(self._persisted_sections_dir(), self._hostname)

    def _persisted_sections_dir(self):
        return os.path.join(cmk.paths.var_dir, "persisted_sections", self.id())

    def get_check_plugin_names(self):
        if self._enforced_check_plugin_names is not None:
            return self._enforced_check_plugin_names
        return self._gather_check_plugin_names()

    @abc.abstractmethod
    def _gather_check_plugin_names(self):
        """
        Returns the list of check plugin names which are supported by
        the device.

        Example: SNMP scan
        """
        raise NotImplementedError()

    def enforce_check_plugin_names(self, check_plugin_names):
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
        raise NotImplementedError()

    @abc.abstractmethod
    def id(self):
        """Return a unique identifier for this data source type
        It is used to identify the different data source types."""
        raise NotImplementedError()

    def name(self):
        """Return a unique (per host) textual identification of the data source

        This name is used to identify this data source instance compared to other
        instances of this data source type and also to instances of other data source
        types.

        It is only used during execution of Check_MK and not persisted. This means
        the algorithm can be changed at any time.
        """
        return ":".join([self.id(), self._hostname, self._ipaddress])

    @abc.abstractmethod
    def describe(self):
        """Return a short textual description of the datasource"""
        raise NotImplementedError()

    def _verify_ipaddress(self):
        if not self._ipaddress:
            raise MKIPAddressLookupError("Host as no IP address configured.")

        if self._ipaddress in ["0.0.0.0", "::"]:
            raise MKIPAddressLookupError(
                "Failed to lookup IP address and no explicit IP address configured")

    def set_max_cachefile_age(self, max_cachefile_age):
        self._max_cachefile_age = max_cachefile_age

    @classmethod
    def disable_data_source_cache(cls):
        cls._no_cache = True

    @classmethod
    def is_agent_cache_disabled(cls):
        return cls._no_cache

    @classmethod
    def get_may_use_cache_file(cls):
        return cls._may_use_cache_file

    @classmethod
    def set_may_use_cache_file(cls, state=True):
        cls._may_use_cache_file = state

    # TODO: Refactor the returned data of this method and self._summary_result()
    # to some wrapped object like CheckResult(...)
    def get_summary_result(self):
        """Returns a three element tuple of state, output and perfdata (list) that summarizes
        the execution result of this data source.

        This is e.g. used for the output of the "Check_MK", "Check_MK Discovery" or
        "Check_MK HW/SW Inventory" services."""

        if not self._exception:
            return self._summary_result()

        exc_msg = "%s" % self._exception

        if isinstance(self._exception, MKEmptyAgentData):
            status = self._exit_code_spec.get("empty_output", 2)

        elif isinstance(self._exception, (MKAgentError, MKIPAddressLookupError, MKSNMPError)):
            status = self._exit_code_spec.get("connection", 2)

        elif isinstance(self._exception, MKTimeout):
            status = self._exit_code_spec.get("timeout", 2)

        else:
            status = self._exit_code_spec.get("exception", 3)

        return status, exc_msg + check_api_utils.state_markers[status], []

    def _summary_result(self):
        """Produce a source specific summary result in case no exception occured.

        When an exception occured while processing a data source, the generic
        self.get_summary_result() will handle this.

        The default is to return empty summary information, which will then be
        ignored by the code that processes the summary result."""
        return 0, "Success", []

    def exception(self):
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
        if not persisted_sections:
            return

        file_path = self._persisted_sections_file_path()

        try:
            os.makedirs(os.path.dirname(file_path))
        except OSError, e:
            if e.errno == 17:  # File exists
                pass
            else:
                raise

        store.save_data_to_file(file_path, persisted_sections, pretty=False)
        self._logger.debug("Stored persisted sections: %s" % (", ".join(persisted_sections.keys())))

    def _update_info_with_persisted_sections(self, host_sections):
        persisted_sections = self._load_persisted_sections()
        if not persisted_sections:
            return host_sections

        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue  # Skip entries of "old" format

            persisted_from, persisted_until, section_info = entry

            # Don't overwrite sections that have been received from the source with this call
            if section_name not in host_sections.sections:
                self._logger.debug("Using persisted section %r" % (section_name))
                host_sections.add_cached_section(section_name, section_info, persisted_from,
                                                 persisted_until)
            else:
                self._logger.debug("Skipping persisted section %r" % (section_name))

        return host_sections

    def _load_persisted_sections(self):
        file_path = self._persisted_sections_file_path()

        persisted_sections = store.load_data_from_file(file_path, {})
        persisted_sections = self._filter_outdated_persisted_sections(persisted_sections)

        if not persisted_sections:
            self._logger.debug("No persisted sections loaded")
        else:
            self._logger.debug(
                "Loaded persisted sections: %s" % (", ".join(persisted_sections.keys())))

        return persisted_sections

    # TODO: This is not race condition free when modifying the data. Either remove
    # the possible write here and simply ignore the outdated sections or lock when
    # reading and unlock after writing
    def _filter_outdated_persisted_sections(self, persisted_sections):
        now = time.time()
        modified = False
        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                persisted_until = entry[0]
            else:
                persisted_until = entry[1]

            if not self._use_outdated_persisted_sections and now > persisted_until:
                self._logger.debug("Persisted section %s is outdated by %d seconds. Deleting it." %
                                   (section_name, now - persisted_until))
                del persisted_sections[section_name]
                modified = True

        if not persisted_sections:
            try:
                os.remove(self._persisted_sections_file_path())
            except OSError:
                pass

        elif modified:
            self._store_persisted_sections(persisted_sections)

        return persisted_sections

    @classmethod
    def use_outdated_persisted_sections(cls):
        cls._use_outdated_persisted_sections = True

    @classmethod
    def set_use_outdated_cache_file(cls, state=True):
        cls._use_outdated_cache_file = state


class CheckMKAgentDataSource(DataSource):
    """Abstract base class for all data sources that work with the Check_MK agent data format"""

    # NOTE: This class is obviously still abstract, but pylint fails to see
    # this, even in the presence of the meta class assignment below, see
    # https://github.com/PyCQA/pylint/issues/179.

    # pylint: disable=abstract-method
    __metaclass__ = abc.ABCMeta

    def __init__(self, hostname, ipaddress):
        super(CheckMKAgentDataSource, self).__init__(hostname, ipaddress)
        self._is_main_agent_data_source = False

    # TODO: We should cleanup these old directories one day. Then we can remove this special case
    def set_main_agent_data_source(self):
        """Tell the data source that it's the main agent based data source

        The data source that is the "main" agent based data source uses the
        cache and persisted directories that existed before the data source
        concept has been added where each data source has it's own set of
        directories.
        """
        self._is_main_agent_data_source = True

    def _gather_check_plugin_names(self):
        return config.discoverable_tcp_checks()

    def _cpu_tracking_id(self):
        return "agent"

    def _cache_dir(self):
        # The main agent has another cache directory to be compatible with older Check_MK
        if self._is_main_agent_data_source:
            return cmk.paths.tcp_cache_dir

        return super(CheckMKAgentDataSource, self)._cache_dir()

    def _persisted_sections_dir(self):
        # The main agent has another cache directory to be compatible with older Check_MK
        if self._is_main_agent_data_source:
            return os.path.join(cmk.paths.var_dir, "persisted")

        return super(CheckMKAgentDataSource, self)._persisted_sections_dir()

    def _convert_to_sections(self, raw_data):
        if config.agent_simulator:
            raw_data = cmk_base.agent_simulator.process(raw_data)

        return self._parse_info(raw_data.split("\n"))

    def _parse_info(self, lines):
        """Split agent output in chunks, splits lines by whitespaces.

        Returns a HostSections() object.
        """
        sections = {}
        # Unparsed info for other hosts. A dictionary, indexed by the piggybacked host name.
        # The value is a list of lines which were received for this host.
        piggybacked_raw_data = {}
        persisted_sections = {}  # handle sections with option persist(...)
        host = None
        section_content = []
        section_options = {}
        agent_cache_info = {}
        separator = None
        encoding = None
        for line in lines:
            line = line.rstrip("\r")
            stripped_line = line.strip()
            if stripped_line[:4] == '<<<<' and stripped_line[-4:] == '>>>>':
                host = stripped_line[4:-4]
                if not host:
                    host = None
                else:
                    host = config.translate_piggyback_host(self._hostname, host)
                    if host == self._hostname:
                        host = None  # unpiggybacked "normal" host

                    # Protect Check_MK against unallowed host names. Normally source scripts
                    # like agent plugins should care about cleaning their provided host names
                    # up, but we need to be sure here to prevent bugs in Check_MK code.
                    # a) Replace spaces by underscores
                    if host:
                        host = host.replace(" ", "_")

            elif host:  # processing data for an other host
                piggybacked_raw_data.setdefault(host, []).append(line)

            # Found normal section header
            # section header has format <<<name:opt1(args):opt2:opt3(args)>>>
            elif stripped_line[:3] == '<<<' and stripped_line[-3:] == '>>>':
                section_header = stripped_line[3:-3]
                headerparts = section_header.split(":")
                section_name = headerparts[0]
                section_options = {}
                for o in headerparts[1:]:
                    opt_parts = o.split("(")
                    opt_name = opt_parts[0]
                    if len(opt_parts) > 1:
                        opt_args = opt_parts[1][:-1]
                    else:
                        opt_args = None
                    section_options[opt_name] = opt_args

                section_content = sections.get(section_name, None)
                if section_content == None:  # section appears in output for the first time
                    section_content = []
                    sections[section_name] = section_content
                try:
                    separator = chr(int(section_options["sep"]))
                except:
                    separator = None

                # Split of persisted section for server-side caching
                if "persist" in section_options:
                    until = int(section_options["persist"])
                    cached_at = int(time.time())  # Estimate age of the data
                    cache_interval = int(until - cached_at)
                    agent_cache_info[section_name] = (cached_at, cache_interval)
                    persisted_sections[section_name] = (cached_at, until, section_content)

                if "cached" in section_options:
                    agent_cache_info[section_name] = tuple(
                        map(int, section_options["cached"].split(",")))

                # The section data might have a different encoding
                encoding = section_options.get("encoding")

            elif stripped_line != '':
                if "nostrip" not in section_options:
                    line = stripped_line

                if encoding:
                    line = config.decode_incoming_string(line, encoding)
                else:
                    line = config.decode_incoming_string(line)

                section_content.append(line.split(separator))

        return HostSections(sections, agent_cache_info, piggybacked_raw_data, persisted_sections)

    # TODO: refactor
    def _summary_result(self):
        agent_info = self._get_agent_info()
        agent_version = agent_info["version"]
        output = []
        if not config.is_cluster(self._hostname) and agent_version != None:
            output.append("Version: %s" % agent_version)

        if not config.is_cluster(self._hostname) and agent_info["agentos"] != None:
            output.append("OS: %s" % agent_info["agentos"])

        return 0, ", ".join(output), []

    def _get_agent_info(self):
        agent_info = {
            "version": "unknown",
            "agentos": "unknown",
        }

        if self._host_sections is None:
            return agent_info

        cmk_section = self._host_sections.sections.get("check_mk")
        if cmk_section:
            for line in cmk_section:
                value = " ".join(line[1:]) if len(line) > 1 else None
                agent_info[line[0][:-1].lower()] = value

        return agent_info


class ManagementBoardDataSource(DataSource):
    """Abstract base class for all data sources that work with the management board configuration"""

    # NOTE: This class is obviously still abstract, but pylint fails to see
    # this, even in the presence of the meta class assignment below, see
    # https://github.com/PyCQA/pylint/issues/179.

    # pylint: disable=abstract-method
    __metaclass__ = abc.ABCMeta

    _for_mgmt_board = True

    def __init__(self, hostname, ipaddress):
        # Do not use the (custom) ipaddress for the host. Use the management board
        # address instead
        ipaddress = self._management_board_ipaddress(hostname)
        super(ManagementBoardDataSource, self).__init__(hostname, ipaddress)
        self._credentials = config.management_credentials_of(self._hostname)

    def _management_board_ipaddress(self, hostname):
        mgmt_ipaddress = config.management_address_of(hostname)

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
