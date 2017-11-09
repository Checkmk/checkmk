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

import ast
import os
import signal
import socket
import subprocess
import sys
import time

import cmk.paths
import cmk.debug
import cmk.cpu_tracking as cpu_tracking
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk.store as store
import cmk_base.config as config
import cmk_base.rulesets as rulesets
import cmk_base.console as console
import cmk_base.checks as checks
import cmk_base.item_state as item_state
import cmk_base.ip_lookup as ip_lookup
import cmk_base.piggyback as piggyback
import cmk_base.snmp as snmp
import cmk_base.core_config as core_config
from cmk_base.exceptions import MKSkipCheck, MKAgentError, MKDataSourceError, MKSNMPError, \
                                MKParseFunctionError, MKTimeout

g_agent_cache_info           = {} # Information about agent caching
g_data_source_errors         = {}

_no_cache                    = False
_no_tcp                      = False
_no_submit                   = False
_enforce_persisting          = False


def get_host_infos(data_sources, hostname, ipaddress, max_cachefile_age=None):
    """Generic function to gather ALL host info data for any host (hosts, nodes, clusters) in Check_MK.

    Returns a dictionary of already parsed info constructs. The structure looks like this:

    {
        ("hostname", "ipaddress"): {
            "section_name": [
                [ "line1field1", ... ],
                [ "line2field1", ... ],
            ]
        }
    }

    Communication errors are not raised through by this functions. All agent related errors are
    stored in the g_data_source_errors construct which can be accessed by the caller to get
    the errors of each data source. The caller should do this, e.g. using
    agent_data.get_data_source_errors_of_host() and transparently display the errors to the users.
    """

    # First abstract clusters/nodes/hosts
    hosts = []
    nodes = config.nodes_of(hostname)
    if nodes is not None:
        for node_hostname in nodes:
            node_ipaddress = ip_lookup.lookup_ip_address(node_hostname)
            hosts.append((node_hostname, node_ipaddress, config.cluster_max_cachefile_age))
    else:
        hosts.append((hostname, ipaddress, config.check_max_cachefile_age))

    if nodes:
        set_use_cachefile()

    # Special agents can produce data for the same check_type on the same host, in this case
    # the section lines need to be extended
    all_host_infos = {}
    for this_hostname, this_ipaddress, this_max_cachfile_age in hosts:
        data_sources.set_max_cachefile_age(this_max_cachfile_age)

        for source_id, source in data_sources.get_data_sources():
            for check_type, lines in source.run(this_hostname, this_ipaddress).items():
                host_infos = all_host_infos.setdefault((this_hostname, this_ipaddress), {})
                host_infos.setdefault(check_type, []).extend(lines)

    return all_host_infos


def get_info_for_check(host_infos, hostname, ipaddress, check_type, for_discovery):
    """Prepares the info construct for a Check_MK check on ANY host

    The info construct is then handed over to the check or discovery functions
    for doing their work.

    If the host is a cluster, the information from all its nodes is used.

    It receives the whole host_infos data and cares about these aspects:

    a) Extract the section for the given check_type
    b) Adds node_info to the info (if check asks for this)
    c) Applies the parse function (if check has some)
    d) Adds extra_sections (if check asks for this)
       and also applies node_info and extra_section handling to this

    It can return an info construct or None when there is no info for this check
    available.
    """
    section_name = check_type.split('.')[0] # make e.g. 'lsi' from 'lsi.arrays'

    # First abstract cluster / non cluster hosts
    host_entries = []
    nodes = config.nodes_of(hostname)
    if nodes != None:
        for node_hostname in nodes:
            # TODO: why is for_discovery handled differently?
            node_name = node_hostname if not for_discovery else None
            host_entries.append(((node_hostname, ip_lookup.lookup_ip_address(node_hostname)), node_name))
    else:
        node_name = hostname if config.clusters_of(hostname) and not for_discovery else None
        host_entries.append(((hostname, ipaddress), node_name))

    # Now extract the sections of the relevant hosts and optionally add the node info
    info = None
    for host_entry, is_node in host_entries:
        try:
            info = host_infos[host_entry][section_name]
        except KeyError:
            continue

        info = _update_info_with_node_info(info, check_type, node_name)
        info = _update_info_with_parse_function(info, check_type)

    if info is None:
        return None

    # TODO: Is this correct? info!
    info = _update_info_with_extra_sections(info, host_infos, hostname, ipaddress, check_type, for_discovery)

    return info


# If the check want's the node info, we add an additional
# column (as the first column) with the name of the node
# or None (in case of non-clustered nodes). On problem arises,
# if we deal with subchecks. We assume that all subchecks
# have the same setting here. If not, let's raise an exception.
# TODO: Why not use the check_type instead of section_name? Inconsistent with node_info!
def _update_info_with_node_info(info, check_type, node_name):
    if check_type not in checks.check_info or not checks.check_info[check_type]["node_info"]:
        return info # unknown check_type or does not want node info -> do nothing

    return _add_nodeinfo(info, node_name)


def _add_nodeinfo(info, nodename):
    new_info = []
    for line in info:
        if len(line) > 0 and type(line[0]) == list:
            new_entry = []
            for entry in line:
                new_entry.append([ nodename ] + entry)
            new_info.append(new_entry)
        else:
            new_info.append([ nodename ] + line)
    return new_info


# TODO: Why not use the check_type instead of section_name? Inconsistent with node_info!
def _update_info_with_extra_sections(info, host_infos, hostname, ipaddress, section_name, for_discovery):
    if section_name not in checks.check_info or not checks.check_info[section_name]["extra_sections"]:
        return info

    # In case of extra_sections the existing info is wrapped into a new list to which all
    # extra sections are appended
    info = [ info ]
    for extra_section_name in checks.check_info[section_name]["extra_sections"]:
        info.append(get_info_for_check(host_infos, hostname, ipaddress, extra_section_name, for_discovery))

    return info


def _update_info_with_parse_function(info, section_name):
    """Some check types define a parse function that is used to transform the info
    somehow. It is applied by this function.

    All exceptions raised by the parse function will be catched and re-raised as
    MKParseFunctionError() exceptions."""

    if section_name not in checks.check_info:
        return info

    parse_function = checks.check_info[section_name]["parse_function"]
    if not parse_function:
        return

    try:
        item_state.set_item_state_prefix(section_name, None)
        return parse_function(info)
    except Exception:
        if cmk.debug.enabled():
            raise
        raise MKParseFunctionError(*sys.exc_info())

    return info



class DataSources(object):
    DS_AGENT     = "agent"
    DS_PIGGY     = "piggyback"
    DS_SNMP      = "snmp"
    DS_MGMT_SNMP = "mgmt_snmp"
    DS_SPECIAL   = "special_%s"

    def __init__(self, hostname):
        super(DataSources, self).__init__()
        self._hostname = hostname
        self._enforced_check_types = None
        self._initialize_data_sources()


    def _initialize_data_sources(self):
        self._sources = {}

        if config.is_all_agents_host(self._hostname):
            self._add_source(self._get_agent_data_source())
            self._add_sources(self._get_special_agent_data_sources())

        elif config.is_all_special_agents_host(self._hostname):
            self._add_sources(self._get_special_agent_data_sources())

        else:
            self._add_source(self._get_agent_data_source())

        self._initialize_management_board_data_sources()
        # TODO: Piggyback datasource


    def _initialize_management_board_data_sources(self):
        if not config.has_management_board(self._hostname):
            return

        # this assumes all snmp checks belong to the management board if there is one with snmp
        # protocol. If at some point we support having both host and management board queried
        # through snmp we have to decide which check belongs where at discovery time and change
        # all data structures, including in the nagios interface...
        is_management_snmp = config.management_protocol(self._hostname) == "snmp"
        if not is_management_snmp:
            return

        self._add_source(SNMPManagementBoardDataSource())


    def _add_sources(self, sources):
        for source in sources:
            self._add_source(source)


    def _add_source(self, source):
        self._sources[source.id()] = source


    def describe_data_sources(self):
        if config.is_all_agents_host(self._hostname):
            return "Contact Check_MK Agent and use all enabled special agents"

        elif config.is_all_special_agents_host(self._hostname):
            return "Use all enabled special agents"

        else:
            return "Contact either Check_MK Agent or use a single special agent"


    def _get_agent_data_source(self):
        # TODO: It's not defined in which order the special agent rules overwrite eachother.
        special_agents = self._get_special_agent_data_sources()
        if special_agents:
            return special_agents[0][1]

        programs = rulesets.host_extra_conf(self._hostname, config.datasource_programs)
        if programs:
            return DSProgramDataSource(programs[0])

        return TCPDataSource()


    def _get_special_agent_data_sources(self):
        special_agents = []

        for agentname, ruleset in config.special_agents.items():
            params = rulesets.host_extra_conf(self._hostname, ruleset)
            if params:
                special_agents[DataSources.DS_SPECIAL % agentname] = SpecialAgentDataSource(agentname, params[0])

        return special_agents


    def get_check_types(self, hostname, ipaddress):
        """Returns the list of check types the caller may execute on the host_infos produced
        by these sources.

        Either returns a list of enforced check types (if set before) or ask each individual
        data source for it's supported check types and return a list of these types.
        """
        if self._enforced_check_types is not None:
            return self._enforced_check_types

        check_types = set()

        for source in self._sources.values():
            check_types.update(source.get_check_types(hostname, ipaddress))

        return list(check_types)


    def enforce_check_types(self, check_types):
        self._enforced_check_types = list(set(check_types))


    def get_data_sources(self):
        # TODO: Ensure deterministic order
        return sorted(self._sources.items())


    def set_max_cachefile_age(self, max_cachefile_age):
        for source_id, source in self.get_data_sources():
            source.set_max_cachefile_age(max_cachefile_age)



class DataSource(object):
    """Abstract base class for all data source classes"""
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

            infos = self._convert_to_infos(raw_data, hostname)
            assert type(infos) == dict
            return infos
        except MKTimeout, e:
            raise
        except Exception, e:
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
            (opt_use_cachefile and ( not _no_cache ) )
            or (config.simulation_mode and not _no_cache) ):
            if cmk_base.utils.cachefile_age(cachefile) <= self._max_cachefile_age or config.simulation_mode:
                result = open(cachefile).read()
                if result:
                    console.verbose("Using data from cachefile %s.\n" % cachefile)
                    return self._from_cache_file(result)
            else:
                console.vverbose("Skipping cache file %s: Too old "
                                 "(age is %d sec, allowed is %s sec)\n" %
                                 (cachefile, cmk_base.utils.cachefile_age(cachefile), self._max_cachefile_age))

        if config.simulation_mode and not _no_cache:
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

        self._save_agent_cache_info(hostname, agent_cache_info)
        piggyback.store_piggyback_info(hostname, piggybacked)
        self._store_persisted_info(hostname, persisted)

        # Add information from previous persisted agent outputs, if those
        # sections are not available in the current output
        # TODO: In the persisted sections the agent_cache_info is missing
        info = self._update_info_with_persisted_infos(info, hostname)

        return info


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


    def _update_info_with_persisted_infos(self, info, hostname):
        # TODO: Use store.load_data_from_file
        file_path = cmk.paths.var_dir + "/persisted/" + hostname
        try:
            persisted = eval(file(file_path).read())
        except:
            return info

        now = time.time()
        modified = False
        for section, entry in persisted.items():
            if len(entry) == 2:
                persisted_from = None
                persisted_until, persisted_section = entry
            else:
                persisted_from, persisted_until, persisted_section = entry
                self._save_agent_cache_info(hostname, {section: (persisted_from, persisted_until - persisted_from)})

            if now < persisted_until or _enforce_persisting:
                if section not in info:
                    info[section] = persisted_section
                    console.vverbose("Added persisted section %s.\n" % section)
            else:
                console.verbose("Persisted section %s is outdated by %d seconds. Deleting it.\n" % (
                        section, now - persisted_until))
                del persisted[section]
                modified = True

        if not persisted:
            try:
                os.remove(file_path)
            except OSError:
                pass
        elif modified:
            self._store_persisted_info(hostname, persisted)

        return info


    def _save_agent_cache_info(self, hostname, agent_cache_info):
        g_agent_cache_info.setdefault(hostname, {}).update(agent_cache_info)



#.
#   .--Agent---------------------------------------------------------------.
#   |                        _                    _                        |
#   |                       / \   __ _  ___ _ __ | |_                      |
#   |                      / _ \ / _` |/ _ \ '_ \| __|                     |
#   |                     / ___ \ (_| |  __/ | | | |_                      |
#   |                    /_/   \_\__, |\___|_| |_|\__|                     |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Real communication with the target system.                           |
#   '----------------------------------------------------------------------'


# Handle SNMP check interval. The idea: An SNMP check should only be
# executed every X seconds. Skip when called too often.
# TODO: The time information was lost in the step we merged the SNMP cache files
#       together. Can't we handle this equal to the persisted agent sections? The
#       check would then be executed but with "old data". That would be nice!
#check_interval = config.check_interval_of(hostname, check_type)
#cache_path = "%s/%s" % (cmk.paths.snmp_cache_dir, hostname)
#if not self._ignore_check_interval \
#   and not _no_submit \
#   and check_interval is not None and os.path.exists(cache_path) \
#   and cmk_base.utils.cachefile_age(cache_path) < check_interval * 60:
#    # cache file is newer than check_interval, skip this check
#    raise MKSkipCheck()
class SNMPDataSource(DataSource):
    def __init__(self):
        super(SNMPDataSource, self).__init__()
        self._check_type_filter_func = None
        self._do_snmp_scan = False
        self._on_error = "raise"
        self._use_snmpwalk_cache = True
        self._ignore_check_interval = False


    def id(self):
        return DataSources.DS_SNMP


    def _from_cache_file(self, raw_data):
        return ast.literal_eval(raw_data)


    def _to_cache_file(self, info):
        return repr(info)


    def set_ignore_check_interval(self, ignore_check_interval):
        self._ignore_check_interval = ignore_check_interval


    def set_use_snmpwalk_cache(self, use_snmpwalk_cache):
        self._use_snmpwalk_cache = use_snmpwalk_cache


    # TODO: Check if this can be dropped
    def set_on_error(self, on_error):
        self._on_error = on_error


    # TODO: Check if this can be dropped
    def set_do_snmp_scan(self, do_snmp_scan):
        self._do_snmp_scan = do_snmp_scan


    def set_check_type_filter(self, filter_func):
        self._check_type_filter_func = filter_func


    # TODO: Only do this once per source object
    def get_check_types(self, hostname, ipaddress):
        if self._check_type_filter_func is None:
            raise MKGeneralException("The check type filter function has not been set")

        return self._check_type_filter_func(hostname, ipaddress, on_error=self._on_error, do_snmp_scan=self._do_snmp_scan)


    def _execute(self, hostname, ipaddress):
    	import cmk_base.inventory_plugins

        self._verify_ipaddress(ipaddress)

        info = {}
        for check_type in self.get_check_types(hostname, ipaddress):
            # Is this an SNMP table check? Then snmp_info specifies the OID to fetch
            # Please note, that if the check_type is foo.bar then we lookup the
            # snmp info for "foo", not for "foo.bar".
            info_type = check_type.split(".")[0]
            if info_type in checks.snmp_info:
                oid_info = checks.snmp_info[info_type]
            elif info_type in cmk_base.inventory_plugins.inv_info:
                oid_info = cmk_base.inventory_plugins.inv_info[info_type].get("snmp_info")
            else:
                oid_info = None

            if oid_info is None:
                continue

            # oid_info can now be a list: Each element  of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            if type(oid_info) == list:
                check_info = []
                for entry in oid_info:
                    check_info_part = snmp.get_snmp_table(hostname, ipaddress, check_type, entry, self._use_snmpwalk_cache)

                    # If at least one query fails, we discard the whole info table
                    if check_info_part is None:
                        check_info = None
                        break
                    else:
                        check_info.append(check_info_part)
            else:
                check_info = snmp.get_snmp_table(hostname, ipaddress, check_type, oid_info, self._use_snmpwalk_cache)

            info[check_type] = check_info

        return info



class SNMPManagementBoardDataSource(SNMPDataSource):
    def id(self):
        return DataSources.DS_MGMT_SNMP


    def _execute(self, hostname, ipaddress):
        # Do not use the (custom) ipaddress for the host. Use the management board
        # address instead
        mgmt_ipaddress = config.management_address(hostname)
        if not self._is_ipaddress(mgmt_ipaddress):
            mgmt_ipaddress = ip_lookup.lookup_ip_address(mgmt_ipaddress)

        return super(SNMPManagementBoardDataSource, self)._execute(hostname, mgmt_ipaddress)


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


class TCPDataSource(CheckMKAgentDataSource):
    def __init__(self):
        super(TCPDataSource, self).__init__()
        self._port = None


    def id(self):
        return DataSources.DS_AGENT


    def set_port(self, port):
        self._port = port


    def _get_port(self, hostname):
        if self._port is not None:
            return self._port
        else:
            return config.agent_port_of(hostname)


    def _execute(self, hostname, ipaddress):
        if _no_tcp:
            raise MKAgentError("Host is unreachable, no usable cache file present")

        self._verify_ipaddress(ipaddress)

        port = self._get_port(hostname)

        encryption_settings = config.agent_encryption_of(hostname)

        s = socket.socket(config.is_ipv6_primary(hostname) and socket.AF_INET6 or socket.AF_INET,
                          socket.SOCK_STREAM)
        s.settimeout(config.tcp_connect_timeout)

        console.vverbose("Connecting via TCP to %s:%d.\n" % (ipaddress, port))
        s.connect((ipaddress, port))
        # Immediately close sending direction. We do not send any data
        # s.shutdown(socket.SHUT_WR)
        try:
            s.setblocking(1)
        except:
            pass
        output = ""
        try:
            while True:
                out = s.recv(4096, socket.MSG_WAITALL)
                if out and len(out) > 0:
                    output += out
                else:
                    break
        except Exception, e:
            # Python seems to skip closing the socket under certain
            # conditions, leaving open filedescriptors and sockets in
            # CLOSE_WAIT. This happens one a timeout (ALERT signal)
            s.close()
            raise

        s.close()

        if len(output) == 0: # may be caused by xinetd not allowing our address
            raise MKAgentError("Empty output from agent at TCP port %d" % port)

        elif len(output) < 16:
            raise MKAgentError("Too short output from agent: %r" % output)

        if encryption_settings["use_regular"] == "enforce" and \
           output.startswith("<<<check_mk>>>"):
            raise MKAgentError("Agent output is plaintext but encryption is enforced by configuration")

        if encryption_settings["use_regular"] != "disabled":
            try:
                # currently ignoring version and timestamp
                #protocol_version = int(output[0:2])

                output = self._decrypt_package(output[2:], encryption_settings["passphrase"])
            except Exception, e:
                if encryption_settings["use_regular"] == "enforce":
                    raise MKAgentError("Failed to decrypt agent output: %s" % e)
                else:
                    # of course the package might indeed have been encrypted but
                    # in an incorrect format, but how would we find that out?
                    # In this case processing the output will fail
                    pass

        return output


    def _decrypt_package(self, encrypted_pkg, encryption_key):
        from Crypto.Cipher import AES
        from hashlib import md5

        unpad = lambda s : s[0:-ord(s[-1])]

        # Adapt OpenSSL handling of key and iv
        def derive_key_and_iv(password, key_length, iv_length):
            d = d_i = ''
            while len(d) < key_length + iv_length:
                d_i = md5(d_i + password).digest()
                d += d_i
            return d[:key_length], d[key_length:key_length+iv_length]

        key, iv = derive_key_and_iv(encryption_key, 32, AES.block_size)
        decryption_suite = AES.new(key, AES.MODE_CBC, iv)
        decrypted_pkg = decryption_suite.decrypt(encrypted_pkg)

        # Strip of fill bytes of openssl
        return unpad(decrypted_pkg)


    def name(self, hostname, ipaddress):
        """Return a unique (per host) textual identification of the data source"""
        return "%s:%d" % (ipaddress, config.agent_port_of(hostname))


    def describe(self, hostname, ipaddress):
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (ipaddress, config.agent_port_of(hostname))



class PiggyBackDataSource(CheckMKAgentDataSource):
    def id(self):
        return DataSources.DS_PIGGY

    def _execute(self, hostname, ipaddress):
        # TODO: Rename to get_piggyback_data()
        return piggyback.get_piggyback_info(hostname) \
               + piggyback.get_piggyback_info(ipaddress)


    def _cache_raw_data(self):
        return False


#.
#   .--Datasoure Programs--------------------------------------------------.
#   |      ____        _                     ____                          |
#   |     |  _ \  __ _| |_ __ _ ___ _ __ ___|  _ \ _ __ ___   __ _         |
#   |     | | | |/ _` | __/ _` / __| '__/ __| |_) | '__/ _ \ / _` |        |
#   |     | |_| | (_| | || (_| \__ \ | | (__|  __/| | | (_) | (_| |_       |
#   |     |____/ \__,_|\__\__,_|___/_|  \___|_|   |_|  \___/ \__, (_)      |
#   |                                                        |___/         |
#   +----------------------------------------------------------------------+
#   | Fetching agent data from program calls instead of an agent           |
#   '----------------------------------------------------------------------'


# Abstract base class for all data source classes that execute external programs
class ProgramDataSource(CheckMKAgentDataSource):
    def _cpu_tracking_id(self):
        return "ds"


    def _execute(self, hostname, ipaddress):
        command_line = self._get_command_line(hostname, ipaddress)
        return self._get_agent_info_program(command_line)


    def _get_agent_info_program(self, commandline):
        exepath = commandline.split()[0] # for error message, hide options!

        console.vverbose("Calling external program %s\n" % commandline)
        p = None
        try:
            if config.monitoring_core == "cmc":
                p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull), # nosec
                                     stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                     preexec_fn=os.setsid, close_fds=True)
            else:
                # We can not create a separate process group when running Nagios
                # Upon reaching the service_check_timeout Nagios only kills the process
                # group of the active check.
                p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull), # nosec
                                     stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                     close_fds=True)
            stdout, stderr = p.communicate()
            exitstatus = p.returncode
        except MKTimeout:
            # On timeout exception try to stop the process to prevent child process "leakage"
            if p:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                p.wait()
            raise
        finally:
            # The stdout and stderr pipe are not closed correctly on a MKTimeout
            # Normally these pipes getting closed after p.communicate finishes
            # Closing them a second time in a OK scenario won't hurt neither..
            if p:
                p.stdout.close()
                p.stderr.close()

        if exitstatus:
            if exitstatus == 127:
                raise MKAgentError("Program '%s' not found (exit code 127)" % exepath)
            else:
                raise MKAgentError("Agent exited with code %d: %s" % (exitstatus, stderr))

        return stdout


    def _get_command_line(self, hostname, ipaddress):
        """Returns the final command line to be executed"""
        raise NotImplementedError()


    def describe(self, hostname, ipaddress):
        """Return a short textual description of the agent"""
        return "Program: %s" % self._get_command_line(hostname, ipaddress)




class DSProgramDataSource(ProgramDataSource):
    def __init__(self, command_template):
        super(DSProgramDataSource, self).__init__()
        self._command_template = command_template


    def id(self):
        return DataSources.DS_AGENT


    def name(self, hostname, ipaddress):
        """Return a unique (per host) textual identification of the data source"""
        program = self._get_command_line(hostname, ipaddress).split(" ")[0]
        return os.path.basename(program)


    def _get_command_line(self, hostname, ipaddress):
        cmd = self._command_template

        cmd = self._translate_legacy_macros(cmd, hostname, ipaddress)
        cmd = self._translate_host_macros(cmd, hostname)

        return cmd


    def _translate_legacy_macros(self, cmd, hostname, ipaddress):
        # Make "legacy" translation. The users should use the $...$ macros in future
        return cmd.replace("<IP>", ipaddress or "").replace("<HOST>", hostname)


    def _translate_host_macros(self, cmd, hostname):
        tags = config.tags_of_host(hostname)
        attrs = core_config.get_host_attributes(hostname, tags)
        if config.is_cluster(hostname):
            parents_list = core_config.get_cluster_nodes_for_config(hostname)
            attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
            attrs.update(core_config.get_cluster_attributes(hostname, parents_list))

        macros = core_config.get_host_macros_from_attributes(hostname, attrs)
        return core_config.replace_macros(cmd, macros)



class SpecialAgentDataSource(ProgramDataSource):
    def __init__(self, special_agent_id, params):
        super(SpecialAgentDataSource, self).__init__()
        self._special_agent_id = special_agent_id
        self._params = params


    def id(self):
        return DataSources.DS_SPECIAL % self._special_agent_id


    # TODO: Can't we make this more specific in case of special agents?
    def get_check_types(self, hostname, ipaddress):
        return checks.discoverable_tcp_checks()


    def name(self, hostname, ipaddress):
        """Return a unique (per host) textual identification of the data source"""
        return self._special_agent_id


    def _get_command_line(self, hostname, ipaddress):
        """Create command line using the special_agent_info"""
        info_func = checks.special_agent_info[self._special_agent_id]
        cmd_arguments = info_func(self._params, hostname, ipaddress)

        special_agents_dir       = cmk.paths.agents_dir + "/special"
        local_special_agents_dir = cmk.paths.local_agents_dir + "/special"

        if os.path.exists(local_special_agents_dir + "/agent_" + self._special_agent_id):
            path = local_special_agents_dir + "/agent_" + self._special_agent_id
        else:
            path = special_agents_dir + "/agent_" + self._special_agent_id

        return path + " " + cmd_arguments

#.
#   .--Use cachefile-------------------------------------------------------.
#   |       _   _                           _           __ _ _             |
#   |      | | | |___  ___    ___ __ _  ___| |__   ___ / _(_) | ___        |
#   |      | | | / __|/ _ \  / __/ _` |/ __| '_ \ / _ \ |_| | |/ _ \       |
#   |      | |_| \__ \  __/ | (_| (_| | (__| | | |  __/  _| | |  __/       |
#   |       \___/|___/\___|  \___\__,_|\___|_| |_|\___|_| |_|_|\___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
# FIXME TODO: Cleanup the whole caching crap

opt_use_cachefile                = False
orig_opt_use_cachefile           = None
orig_check_max_cachefile_age     = None
orig_cluster_max_cachefile_age   = None
orig_inventory_max_cachefile_age = None

def get_use_cachefile():
    return opt_use_cachefile

def set_use_cachefile(state=True):
    global opt_use_cachefile, orig_opt_use_cachefile
    orig_opt_use_cachefile = opt_use_cachefile
    opt_use_cachefile = state


def restore_use_cachefile():
    global opt_use_cachefile, orig_opt_use_cachefile
    if orig_opt_use_cachefile != None:
        opt_use_cachefile = orig_opt_use_cachefile
        orig_opt_use_cachefile = None


# TODO: Why 1000000000? Can't we really clean this up to a global variable which can
# be toggled to enforce the cache usage (if available). This way we would not need
# to store the original values of the different caches and modify them etc.
def enforce_using_agent_cache():
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if config.check_max_cachefile_age != 1000000000:
        orig_check_max_cachefile_age     = config.check_max_cachefile_age
        orig_cluster_max_cachefile_age   = config.cluster_max_cachefile_age
        orig_inventory_max_cachefile_age = config.inventory_max_cachefile_age

    config.check_max_cachefile_age     = 1000000000
    config.cluster_max_cachefile_age   = 1000000000
    config.inventory_max_cachefile_age = 1000000000


def restore_original_agent_caching_usage():
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if orig_check_max_cachefile_age != None:
        config.check_max_cachefile_age     = orig_check_max_cachefile_age
        config.cluster_max_cachefile_age   = orig_cluster_max_cachefile_age
        config.inventory_max_cachefile_age = orig_inventory_max_cachefile_age

        orig_check_max_cachefile_age     = None
        orig_cluster_max_cachefile_age   = None
        orig_inventory_max_cachefile_age = None


#.
#   .--Misc.---------------------------------------------------------------.
#   |                         __  __ _                                     |
#   |                        |  \/  (_)___  ___                            |
#   |                        | |\/| | / __|/ __|                           |
#   |                        | |  | | \__ \ (__ _                          |
#   |                        |_|  |_|_|___/\___(_)                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Different helper functions                                           |
#   '----------------------------------------------------------------------'

# TODO: Clean this up
def get_agent_cache_info():
    return g_agent_cache_info


def cleanup_host_caches():
    for cache in [
            g_agent_cache_info,
            g_data_source_errors ]:
        cache.clear()


def add_data_source_error(hostname, ipaddress, data_source, e):
    g_data_source_errors.setdefault(hostname, {}).setdefault(data_source.name(hostname, ipaddress), []).append(e)


def has_data_source_errors(hostname, ipaddress, data_source):
    return bool(get_data_source_errors(hostname, ipaddress, data_source))


def get_data_source_errors(hostname, ipaddress, data_source):
    return g_data_source_errors.get(hostname, {}).get(data_source.name(hostname, ipaddress))


def get_data_source_errors_of_host(hostname, ipaddress):
    return g_data_source_errors.get(hostname, {})


def disable_agent_cache():
    global _no_cache
    _no_cache = True


def is_agent_cache_disabled():
    return _no_cache


def disable_tcp():
    global _no_tcp
    _no_tcp = True


def disable_submit():
    global _no_submit
    _no_submit = True


def do_submit():
    return not _no_submit


def enforce_persisting():
    global _enforce_persisting
    _enforce_persisting = True
