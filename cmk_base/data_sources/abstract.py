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
import time

import cmk.debug
import cmk.paths
import cmk.store as store
import cmk.cpu_tracking as cpu_tracking
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.piggyback as piggyback
import cmk_base.checks as checks
from cmk_base.exceptions import MKSkipCheck, MKAgentError, MKDataSourceError, MKSNMPError, \
                                MKParseFunctionError, MKTimeout

from .host_info import HostInfo

class DataSource(object):
    """Abstract base class for all data source classes"""
    # TODO: Clean these options up!
    # Set by the user via command line to prevent using cached information
    _no_cache = False
    # Set by the code in different situations where we recommend,
    # but not enforce, to use the cache
    _use_cachefile = False
    _use_outdated_persisted_sections = False

    def __init__(self):
        super(DataSource, self).__init__()
        self._max_cachefile_age = None


    def run(self, hostname, ipaddress):
        """Wrapper for self._execute() that unifies several things:

        a) Exception handling
        b) Caching of raw data
        c) CPU tracking

        Exceptions: All exceptions except MKTimeout are wrapped into
        MKDataSourceError exceptions."""
        try:
            cpu_tracking.push_phase(self._cpu_tracking_id())

            # The "raw data" is the raw byte string returned by the source for
            # CheckMKAgentDataSource sources. The SNMPDataSource source already
            # return the final info data structure.
            if self._cache_raw_data():
                raw_data = self._read_cache_file(hostname)
                if not raw_data:
                    raw_data = self._execute(hostname, ipaddress)
                    self._write_cache_file(hostname, raw_data)

            else:
                raw_data = self._execute(hostname, ipaddress)

            host_info = self._convert_to_infos(raw_data, hostname)
            assert isinstance(host_info, HostInfo)
            return host_info
        except MKTimeout, e:
            raise
        except Exception, e:
            if cmk.debug.enabled():
                raise
            raise MKDataSourceError(self.name(hostname, ipaddress), e)
        finally:
            cpu_tracking.pop_phase()


    def _execute(self, hostname, ipaddress):
        """Fetches the current agent data from the source specified with
        hostname and ipaddress and returns the result as "raw data" that is
        later converted by self._convert_to_infos() to info data structures.

        The "raw data" is the raw byte string returned by the source for
        CheckMKAgentDataSource sources. The SNMPDataSource source already
        return the final info data structure."""
        # TODO: Shouldn't we ensure decoding to unicode here?
        raise NotImplementedError()


    def _read_cache_file(self, hostname):
        # TODO: Use store.load_data_from_file
        # TODO: Refactor this to be more readable
        assert self._max_cachefile_age is not None

        cachefile = self._cache_file_path(hostname)

        if os.path.exists(cachefile) and (
            (self._use_cachefile and ( not self._no_cache ) )
            or (config.simulation_mode and not self._no_cache) ):
            if cmk_base.utils.cachefile_age(cachefile) <= self._max_cachefile_age or config.simulation_mode:
                result = open(cachefile).read()
                if result:
                    console.verbose("Using data from cachefile %s.\n" % cachefile)
                    return self._from_cache_file(result)
            else:
                console.vverbose("Skipping cache file %s: Too old "
                                 "(age is %d sec, allowed is %s sec)\n" %
                                 (cachefile, cmk_base.utils.cachefile_age(cachefile), self._max_cachefile_age))

        if config.simulation_mode and not self._no_cache:
            raise MKAgentError("Simulation mode and no cachefile present.")


    def _write_cache_file(self, hostname, output):
        cachefile = self._cache_file_path(hostname)

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

        # TODO: Use cmk.store!
        try:
            f = open(cachefile, "w+")
            f.write(self._to_cache_file(output))
            f.close()
        except Exception, e:
            raise MKGeneralException("Cannot write cache file %s: %s" % (cachefile, e))


    def _from_cache_file(self, raw_data):
        return raw_data


    def _to_cache_file(self, raw_data):
        return raw_data


    def _cache_raw_data(self):
        return True


    def _convert_to_infos(self, raw_data, hostname):
        """See _execute() for details"""
        raise NotImplementedError()


    def _cache_file_path(self, hostname):
        return os.path.join(self._cache_dir(), hostname)


    def _cache_dir(self):
        return os.path.join(cmk.paths.data_source_cache_dir, self.id())


    def get_check_types(self, hostname, ipaddress):
        raise NotImplementedError()


    def _cpu_tracking_id(self):
        raise NotImplementedError()


    def id(self):
        """Return a unique identifier for this data source"""
        raise NotImplementedError()


    def name(self, hostname, ipaddress):
        """Return a unique (per host) textual identification of the data source"""
        raise NotImplementedError()


    def describe(self, hostname, ipaddress):
        """Return a short textual description of the datasource"""
        raise NotImplementedError()


    def _verify_ipaddress(self, ipaddress):
        if not ipaddress:
            raise MKGeneralException("Host as no IP address configured.")

        if ipaddress in [ "0.0.0.0", "::" ]:
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
    def get_use_cachefile(cls):
        return cls._use_cachefile


    @classmethod
    def set_use_cachefile(cls, state=True):
        cls._use_cachefile = state



class CheckMKAgentDataSource(DataSource):
    """Abstract base class for all data sources that work with the Check_MK agent data format"""
    def get_check_types(self, *args, **kwargs):
        return checks.discoverable_tcp_checks()


    def _cpu_tracking_id(self):
        return "agent"


    # The agent has another cache directory to be compatible with older Check_MK
    def _cache_dir(self):
        return cmk.paths.tcp_cache_dir


    def _convert_to_infos(self, raw_data, hostname):
        if config.agent_simulator:
            raw_data = cmk_base.agent_simulator.process(raw_data)

        info, piggybacked, persisted, agent_cache_info = self._parse_info(raw_data.split("\n"), hostname)

        host_info = HostInfo(info, agent_cache_info)

        piggyback.store_piggyback_info(hostname, piggybacked)
        self._store_persisted_info(hostname, persisted)

        # Add information from previous persisted agent outputs, if those
        # sections are not available in the current output
        host_info = self._update_info_with_persisted_infos(host_info, hostname)

        return host_info


    def _parse_info(self, lines, hostname):
        """Split agent output in chunks, splits lines by whitespaces.

        Returns a tuple of:

            1. A dictionary from "sectionname" to a list of rows
            2. piggy-backed data for other hosts
            3. Sections to be persisted for later usage
            4. Agent cache information (dict section name -> (cached_at, cache_interval))

        """
        info = {}
        piggybacked = {} # unparsed info for other hosts
        persist = {} # handle sections with option persist(...)
        host = None
        section = []
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
                    host = piggyback.translate_piggyback_host(hostname, host)
                    if host == hostname:
                        host = None # unpiggybacked "normal" host

                    # Protect Check_MK against unallowed host names. Normally source scripts
                    # like agent plugins should care about cleaning their provided host names
                    # up, but we need to be sure here to prevent bugs in Check_MK code.
                    # a) Replace spaces by underscores
                    if host:
                        host = host.replace(" ", "_")

            elif host: # processing data for an other host
                piggybacked.setdefault(host, []).append(line)

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

                section = info.get(section_name, None)
                if section == None: # section appears in output for the first time
                    section = []
                    info[section_name] = section
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
                    persist[section_name] = ( cached_at, until, section )

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

                section.append(line.split(separator))

        return info, piggybacked, persist, agent_cache_info


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

    def _store_persisted_info(self, hostname, persisted):
        dirname = cmk.paths.var_dir + "/persisted/"
        if persisted:
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            file_path = "%s/%s" % (dirname, hostname)
            store.save_data_to_file(file_path, persisted, pretty=False)

            console.verbose("Persisted sections %s.\n" % ", ".join(persisted.keys()))


    # TODO: This is not race condition free when modifying the data. Either remove
    # the possible write here and simply ignore the outdated sections or lock when
    # reading and unlock after writing
    def _update_info_with_persisted_infos(self, host_info, hostname):
        # TODO: Use store.load_data_from_file
        file_path = cmk.paths.var_dir + "/persisted/" + hostname
        try:
            persisted = eval(file(file_path).read())
        except:
            return host_info

        now = time.time()
        modified = False
        for section_name, entry in persisted.items():
            if len(entry) == 2:
                persisted_from = None
                persisted_until, section = entry
            else:
                persisted_from, persisted_until, section = entry

            if now < persisted_until or self._use_outdated_persisted_sections:
                if section_name not in host_info.info:
                    host_info.add_cached_section(section_name, section, persisted_from, persisted_until)
                    console.vverbose("Using persisted section %s.\n" % section_name)
            else:
                console.verbose("Persisted section %s is outdated by %d seconds. Deleting it.\n" % (
                        section_name, now - persisted_until))
                del persisted[section_name]
                modified = True

        if not persisted:
            try:
                os.remove(file_path)
            except OSError:
                pass

        elif modified:
            self._store_persisted_info(hostname, persisted)

        return host_info


    @classmethod
    def use_outdated_persisted_sections(cls):
        cls._use_outdated_persisted_sections = True
