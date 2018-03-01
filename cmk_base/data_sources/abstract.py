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

import cmk.debug
import cmk.paths
import cmk.store as store
import cmk.cpu_tracking as cpu_tracking
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.ip_lookup as ip_lookup
import cmk_base.piggyback as piggyback
import cmk_base.checks as checks
import cmk_base.ip_lookup as ip_lookup
from cmk_base.exceptions import MKSkipCheck, MKAgentError, MKDataSourceError, MKSNMPError, \
                                MKParseFunctionError, MKTimeout

from .host_sections import HostSections

class DataSource(object):
    """Abstract base class for all data source classes"""

    _for_mgmt_board = False

    # TODO: Clean these options up! We need to change all call sites to use
    #       a single DataSources() object during processing first. Then we
    #       can change these class attributes to object attributes.
    #
    # Set by the user via command line to prevent using cached information at all
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
        self._logger = console.logger
        self._max_cachefile_age = None
        self._enforced_check_plugin_names = None


    def run(self, hostname=None, ipaddress=None, get_raw_data=False):
        """Wrapper for self._execute() that unifies several things:

        a) Exception handling
        b) Caching of raw data
        c) CPU tracking

        Exceptions: All exceptions except MKTimeout are wrapped into
        MKDataSourceError exceptions.

        Both hostname and ipaddress are optional, used for virtual
        Check_MK clusters."""

        if hostname is not None:
            self._hostname = hostname
        if ipaddress is not None:
            self._ipaddress = ipaddress

        try:
            cpu_tracking.push_phase(self._cpu_tracking_id())

            raw_data, is_cached_data = self._get_raw_data()
            if get_raw_data:
                return raw_data

            host_sections = self._convert_to_sections(raw_data)
            assert isinstance(host_sections, HostSections)

            if host_sections.persisted_sections and not is_cached_data:
                self._store_persisted_sections(host_sections.persisted_sections)

            # Add information from previous persisted infos
            host_sections = self._update_info_with_persisted_sections(host_sections)

            return host_sections
        except MKTimeout, e:
            raise
        except Exception, e:
            if cmk.debug.enabled():
                raise
            raise MKDataSourceError(self.name(), e)
        finally:
            cpu_tracking.pop_phase()


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
            self._logger.verbose("[%s] Use cached data" % self.id())
            return raw_data, True

        elif raw_data is None and config.simulation_mode:
            raise MKAgentError("Got no data (Simulation mode enabled and no cachefile present)")

        self._logger.verbose("[%s] Execute data source" % self.id())
        raw_data = self._execute()
        self._write_cache_file(raw_data)
        return raw_data, False


    def run_raw(self):
        """Small wrapper for self.run() which always returns raw data source data"""
        return self.run(get_raw_data=True)


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
            self._logger.debug("[%s] Not using cache (Does not exist)" % self.id())
            return

        if self._no_cache:
            self._logger.debug("[%s] Not using cache (Cache usage disabled)" % self.id())
            return

        if not self._may_use_cache_file and not config.simulation_mode:
            self._logger.debug("[%s] Not using cache (Don't try it)" % self.id())
            return

        may_use_outdated = config.simulation_mode or self._use_outdated_cache_file
        if not may_use_outdated and cmk_base.utils.cachefile_age(cachefile) > self._max_cachefile_age:
            self._logger.debug("[%s] Not using cache (Too old. Age is %d sec, allowed is %s sec)" %
                             (self.id(), cmk_base.utils.cachefile_age(cachefile), self._max_cachefile_age))
            return

        # TODO: Use some generic store file read function to generalize error handling,
        # but there is currently no function that simply reads data from the file
        result = open(cachefile).read()
        if not result:
            self._logger.debug("[%s] Not using cache (Empty)" % self.id())
            return

        self._logger.verbose("[%s] Using data from cache file %s" % (self.id(), cachefile))
        return self._from_cache_file(result)


    def _write_cache_file(self, raw_data):
        cachefile = self._cache_file_path()

        try:
            try:
                os.makedirs(os.path.dirname(cachefile))
            except OSError, e:
                if e.errno == 17: # File exists
                    pass
                else:
                    raise
        except Exception, e:
            raise MKGeneralException("Cannot create directory %r: %s" % (os.path.dirname(cachefile), e))

        self._logger.verbose("[%s] Write data to cache file %s" % (self.id(), cachefile))
        try:
            store.save_file(cachefile, self._to_cache_file(raw_data))
        except Exception, e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (cachefile, e))


    def _from_cache_file(self, raw_data):
        return raw_data


    def _to_cache_file(self, raw_data):
        return raw_data


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


    def _gather_check_plugin_names(self):
        raise NotImplementedError()


    def enforce_check_plugin_names(self, check_plugin_names):
        self._enforced_check_plugin_names = check_plugin_names


    def _cpu_tracking_id(self):
        raise NotImplementedError()


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


    def describe(self):
        """Return a short textual description of the datasource"""
        raise NotImplementedError()


    def _verify_ipaddress(self):
        if not self._ipaddress:
            raise MKGeneralException("Host as no IP address configured.")

        if self._ipaddress in [ "0.0.0.0", "::" ]:
            raise MKGeneralException("Failed to lookup IP address and no explicit IP address configured")


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
            if e.errno == 17: # File exists
                pass
            else:
                raise

        store.save_data_to_file(file_path, persisted_sections, pretty=False)
        self._logger.debug("[%s] Stored persisted sections: %s" % (self.id(), ", ".join(persisted_sections.keys())))


    def _update_info_with_persisted_sections(self, host_sections):
        persisted_sections = self._load_persisted_sections()
        if not persisted_sections:
            return host_sections

        for section_name, entry in persisted_sections.items():
            if len(entry) == 2:
                continue # Skip entries of "old" format

            persisted_from, persisted_until, section_info = entry

            # Don't overwrite sections that have been received from the source with this call
            if section_name not in host_sections.sections:
                self._logger.debug("[%s] Using persisted section %r" % (self.id(), section_name))
                host_sections.add_cached_section(section_name, section_info, persisted_from, persisted_until)
            else:
                self._logger.debug("[%s] Skipping persisted section %r" % (self.id(), section_name))

        return host_sections


    def _load_persisted_sections(self):
        file_path = self._persisted_sections_file_path()

        persisted_sections = store.load_data_from_file(file_path, {})
        persisted_sections = self._filter_outdated_persisted_sections(persisted_sections)

        if not persisted_sections:
            self._logger.debug("[%s] No persisted sections loaded" % (self.id()))
        else:
            self._logger.debug("[%s] Loaded persisted sections: %s" % (self.id(), ", ".join(persisted_sections.keys())))

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
                self._logger.debug("[%s] Persisted section %s is outdated by %d seconds. Deleting it." %
                                                       (self.id(), section_name, now - persisted_until))
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


    def _gather_check_plugin_names(self, *args, **kwargs):
        return checks.discoverable_tcp_checks()


    def _cpu_tracking_id(self):
        return "agent"


    def _cache_dir(self):
        # The main agent has another cache directory to be compatible with older Check_MK
        if self._is_main_agent_data_source:
            return cmk.paths.tcp_cache_dir
        else:
            return super(CheckMKAgentDataSource, self)._cache_dir()


    def _persisted_sections_dir(self):
        # The main agent has another cache directory to be compatible with older Check_MK
        if self._is_main_agent_data_source:
            return os.path.join(cmk.paths.var_dir, "persisted")
        else:
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
        persisted_sections = {} # handle sections with option persist(...)
        host = None
        section_content = []
        section_options = {}
        agent_cache_info = {}
        separator = None
        encoding  = None
        for line in lines:
            line = line.rstrip("\r")
            stripped_line = line.strip()
            if stripped_line[:4] == '<<<<' and stripped_line[-4:] == '>>>>':
                host = stripped_line[4:-4]
                if not host:
                    host = None
                else:
                    host = piggyback.translate_piggyback_host(self._hostname, host)
                    if host == self._hostname:
                        host = None # unpiggybacked "normal" host

                    # Protect Check_MK against unallowed host names. Normally source scripts
                    # like agent plugins should care about cleaning their provided host names
                    # up, but we need to be sure here to prevent bugs in Check_MK code.
                    # a) Replace spaces by underscores
                    if host:
                        host = host.replace(" ", "_")

            elif host: # processing data for an other host
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
                if section_content == None: # section appears in output for the first time
                    section_content = []
                    sections[section_name] = section_content
                try:
                    separator = chr(int(section_options["sep"]))
                except:
                    separator = None

                # Split of persisted section for server-side caching
                if "persist" in section_options:
                    until = int(section_options["persist"])
                    cached_at = int(time.time()) # Estimate age of the data
                    cache_interval = int(until - cached_at)
                    agent_cache_info[section_name] = (cached_at, cache_interval)
                    persisted_sections[section_name] = ( cached_at, until, section_content )

                if "cached" in section_options:
                    agent_cache_info[section_name] = tuple(map(int, section_options["cached"].split(",")))

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



class ManagementBoardDataSource(DataSource):
    """Abstract base class for all data sources that work with the management board configuration"""
    _for_mgmt_board = True

    def __init__(self, hostname, ipaddress):
        # Do not use the (custom) ipaddress for the host. Use the management board
        # address instead
        ipaddress = self._management_board_ipaddress(hostname)
        super(ManagementBoardDataSource, self).__init__(hostname, ipaddress)


    def _credentials(self):
        return config.management_credentials_of(self._hostname)


    def _management_board_ipaddress(self, hostname):
        mgmt_ipaddress = config.management_address_of(hostname)

        if not self._is_ipaddress(mgmt_ipaddress):
            return ip_lookup.lookup_ip_address(mgmt_ipaddress)
        else:
            return mgmt_ipaddress


    # TODO: Why is it used only here?
    def _is_ipaddress(self, address):
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
