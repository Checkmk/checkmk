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

import sys

import cmk.utils.debug

import cmk_base.config as config
import cmk_base.caching as caching
import cmk_base.ip_lookup as ip_lookup
import cmk_base.item_state as item_state
import cmk_base.check_utils

from cmk_base.exceptions import MKParseFunctionError


class HostSections(object):
    """A wrapper class for the host information read by the data sources

    It contains the following information:

        1. sections:                A dictionary from section_name to a list of rows,
                                    the section content
        2. piggybacked_raw_data:    piggy-backed data for other hosts
        3. persisted_sections:      Sections to be persisted for later usage
        4. cache_info:              Agent cache information
                                    (dict section name -> (cached_at, cache_interval))
    """
    def __init__(self,
                 sections=None,
                 cache_info=None,
                 piggybacked_raw_data=None,
                 persisted_sections=None):
        super(HostSections, self).__init__()
        self.sections = sections if sections is not None else {}
        self.cache_info = cache_info if cache_info is not None else {}
        self.piggybacked_raw_data = piggybacked_raw_data if piggybacked_raw_data is not None else {}
        self.persisted_sections = persisted_sections if persisted_sections is not None else {}

    # TODO: It should be supported that different sources produce equal sections.
    # this is handled for the self.sections data by simply concatenating the lines
    # of the sections, but for the self.cache_info this is not done. Why?
    # TODO: checking.execute_check() is using the oldest cached_at and the largest interval.
    #       Would this be correct here?
    def update(self, host_sections):
        """Update this host info object with the contents of another one"""
        for section_name, lines in host_sections.sections.items():
            self.sections.setdefault(section_name, []).extend(lines)

        for hostname, lines in host_sections.piggybacked_raw_data.items():
            self.piggybacked_raw_data.setdefault(hostname, []).extend(lines)

        if host_sections.cache_info:
            self.cache_info.update(host_sections.cache_info)

        if host_sections.persisted_sections:
            self.persisted_sections.update(host_sections.persisted_sections)

    def add_cached_section(self, section_name, section, persisted_from, persisted_until):
        self.cache_info[section_name] = (persisted_from, persisted_until - persisted_from)
        self.sections[section_name] = section


class MultiHostSections(object):
    """Container object for wrapping the host sections of a host being processed
    or multiple hosts when a cluster is processed. Also holds the functionality for
    merging these information together for a check"""
    def __init__(self):
        super(MultiHostSections, self).__init__()
        self._config_cache = config.get_config_cache()
        self._multi_host_sections = {}
        self._section_content_cache = caching.DictCache()

    def add_or_get_host_sections(self, hostname, ipaddress, deflt=None):
        if deflt is None:
            deflt = HostSections()
        return self._multi_host_sections.setdefault((hostname, ipaddress), deflt)

    def get_host_sections(self):
        return self._multi_host_sections

    def get_section_content(self,
                            hostname,
                            ipaddress,
                            check_plugin_name,
                            for_discovery,
                            service_description=None):
        """Prepares the section_content construct for a Check_MK check on ANY host

        The section_content construct is then handed over to the check, inventory or
        discovery functions for doing their work.

        If the host is a cluster, the sections from all its nodes is merged together
        here. Optionally the node info is added to the nodes section content.

        It handles the whole data and cares about these aspects:

        a) Extract the section_content for the given check_plugin_name
        b) Adds node_info to the section_content (if check asks for this)
        c) Applies the parse function (if check has some)
        d) Adds extra_sections (if check asks for this)
           and also applies node_info and extra_section handling to this

        It can return an section_content construct or None when there is no section content
        for this check available.
        """

        section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
        nodes_of_clustered_service = self._get_nodes_of_clustered_service(
            hostname, service_description)
        cache_key = (hostname, ipaddress, section_name, for_discovery,
                     bool(nodes_of_clustered_service))

        try:
            return self._section_content_cache[cache_key]
        except KeyError:
            section_content = self._get_section_content(hostname, ipaddress, check_plugin_name,
                                                        section_name, for_discovery,
                                                        nodes_of_clustered_service)
            self._section_content_cache[cache_key] = section_content
            return section_content

    def _get_nodes_of_clustered_service(self, hostname, service_description):
        """Returns the node names if a service is clustered, otherwise 'None' in order to
        decide whether we collect section content of the host or the nodes.

        For real hosts or nodes for which the service is not clustered we return 'None',
        thus the caching works as before.

        If a service is assigned to a cluster we receive the real nodename. In this
        case we have to sort out data from the nodes for which the same named service
        is not clustered (Clustered service for overlapping clusters).

        We also use the result for the section cache.
        """
        if not service_description:
            return

        host_config = self._config_cache.get_host_config(hostname)
        nodes = host_config.nodes

        if nodes is None:
            return

        return [
            nodename for nodename in nodes
            if hostname == self._config_cache.host_of_clustered_service(
                nodename, service_description)
        ]

    def _get_section_content(self, hostname, ipaddress, check_plugin_name, section_name,
                             for_discovery, nodes_of_clustered_service):

        # First abstract cluster / non cluster hosts
        host_entries = self._get_host_entries(hostname, ipaddress)

        # Now get the section_content from the required hosts and merge them together to
        # a single section_content. For each host optionally add the node info.
        section_content = None
        for host_entry in host_entries:
            if nodes_of_clustered_service and host_entry[0] not in nodes_of_clustered_service:
                continue

            try:
                host_section_content = self._multi_host_sections[host_entry].sections[section_name]
            except KeyError:
                continue

            host_section_content = self._update_with_node_column(host_section_content,
                                                                 check_plugin_name, host_entry[0],
                                                                 for_discovery)

            if section_content is None:
                section_content = []

            section_content += host_section_content

        if section_content is None:
            return None

        assert isinstance(section_content, list)

        section_content = self._update_with_parse_function(section_content, section_name)
        section_content = self._update_with_extra_sections(section_content, hostname, ipaddress,
                                                           section_name, for_discovery)
        return section_content

    def _get_host_entries(self, hostname, ipaddress):
        host_config = self._config_cache.get_host_config(hostname)
        if host_config.nodes is None:
            return [(hostname, ipaddress)]

        return [(node_hostname, ip_lookup.lookup_ip_address(node_hostname))
                for node_hostname in host_config.nodes]

    def _update_with_node_column(self, section_content, check_plugin_name, hostname, for_discovery):
        """Add cluster node information to the section content

        If the check want's the node column, we add an additional column (as the first column) with the
        name of the node or None in case of non-clustered nodes.

        Whether or not a node info is requested by a check is not a property of the agent section. Each
        check/subcheck can define the requirement on it's own.

        When called for the discovery, the node name is always set to "None". During the discovery of
        services we behave like a non-cluster because we don't know whether or not the service will
        be added to the cluster or the node. This decision is made later during creation of the
        configuation. This means that the discovery function must work independent from the node info.
        """
        if check_plugin_name not in config.check_info or not config.check_info[check_plugin_name][
                "node_info"]:
            return section_content  # unknown check_plugin_name or does not want node info -> do nothing

        node_name = None
        if not for_discovery and self._config_cache.clusters_of(hostname):
            node_name = hostname

        return self._add_node_column(section_content, node_name)

    def _add_node_column(self, section_content, nodename):
        new_section_content = []
        for line in section_content:
            if len(line) > 0 and isinstance(line[0], list):
                new_entry = []
                for entry in line:
                    new_entry.append([nodename] + entry)
                new_section_content.append(new_entry)
            else:
                new_section_content.append([nodename] + line)
        return new_section_content

    def _update_with_extra_sections(self, section_content, hostname, ipaddress, section_name,
                                    for_discovery):
        """Adds additional agent sections to the section_content the check receives.

        Please note that this is not a check/subcheck individual setting. This option is related
        to the agent section.
        """
        if section_name not in config.check_info or not config.check_info[section_name][
                "extra_sections"]:
            return section_content

        # In case of extra_sections the existing info is wrapped into a new list to which all
        # extra sections are appended
        section_content = [section_content]
        for extra_section_name in config.check_info[section_name]["extra_sections"]:
            section_content.append(
                self.get_section_content(hostname, ipaddress, extra_section_name, for_discovery))

        return section_content

    def _update_with_parse_function(self, section_content, section_name):
        """Transform the section_content using the defined parse functions.

        Some checks define a parse function that is used to transform the section_content
        somehow. It is applied by this function.

        Please note that this is not a check/subcheck individual setting. This option is related
        to the agent section.

        All exceptions raised by the parse function will be catched and re-raised as
        MKParseFunctionError() exceptions."""

        if section_name not in config.check_info:
            return section_content

        parse_function = config.check_info[section_name]["parse_function"]
        if not parse_function:
            return section_content

        # TODO: Item state needs to be handled in local objects instead of the
        # item_state._cached_item_states object
        orig_item_state_prefix = item_state.get_item_state_prefix()
        try:
            item_state.set_item_state_prefix(section_name, None)
            return parse_function(section_content)
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            raise MKParseFunctionError(*sys.exc_info())
        finally:
            item_state.set_item_state_prefix(*orig_item_state_prefix)

        return section_content

    def get_check_plugin_names(self):
        # TODO: There is a function 'section_name_of' in check_utils.py
        # but no inverse function, ie. get all subchecks of main check.
        check_keys = set(config.check_info.keys())
        check_plugin_names = set()
        for v in self._multi_host_sections.values():
            for k in v.sections.keys():
                for check_k in check_keys:
                    if check_k.startswith(k):
                        check_plugin_names.add(check_k)
        return list(check_plugin_names)
