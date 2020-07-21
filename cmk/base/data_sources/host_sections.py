#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections.abc
import sys
from typing import Any, Callable, NamedTuple, cast, Dict, List, Optional, Tuple, Union

import cmk.utils.debug
from cmk.utils.check_utils import section_name_of
from cmk.utils.type_defs import (
    CheckPluginNameStr,
    HostAddress,
    HostName,
    ParsedSectionName,
    SectionName,
    ServiceName,
    SourceType,
)

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.caching as caching
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.item_state as item_state
from cmk.base.api.agent_based.type_defs import (
    AgentParseFunction,
    AgentSectionPlugin,
    SNMPParseFunction,
    SNMPSectionPlugin,
)
from cmk.base.api.agent_based.utils import parse_to_string_table
from cmk.base.check_api_utils import HOST_ONLY as LEGACY_HOST_ONLY
from cmk.base.check_api_utils import HOST_PRECEDENCE as LEGACY_HOST_PRECEDENCE
from cmk.base.check_api_utils import MGMT_ONLY as LEGACY_MGMT_ONLY
from cmk.base.check_utils import (
    AbstractSectionContent,
    FinalSectionContent,
    ParsedSectionContent,
)
from cmk.base.exceptions import MKParseFunctionError

from ._abstract import ABCHostSections

HostKey = NamedTuple("HostKey", [
    ("hostname", HostName),
    ("ipaddress", Optional[HostAddress]),
    ("source_type", SourceType),
])


class MultiHostSections(collections.abc.MutableMapping):
    """Container object for wrapping the host sections of a host being processed
    or multiple hosts when a cluster is processed. Also holds the functionality for
    merging these information together for a check"""
    def __init__(self, data: Optional[Dict[HostKey, ABCHostSections]] = None) -> None:
        super(MultiHostSections, self).__init__()
        self._data: Dict[HostKey, ABCHostSections] = {} if data is None else data
        self._config_cache = config.get_config_cache()
        self._section_content_cache = caching.DictCache()
        # This is not quite the same as section_content_cache.
        # It is introduced for the changed data handling with the migration
        # to 'agent_based' plugins.
        # It holds the result of the parse_function along with the
        # cache info of the raw section that was used.
        self._parsed_sections = caching.DictCache()
        self._parsed_to_raw_map = caching.DictCache()

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return self._data.__iter__()

    def __getitem__(self, key: HostKey):
        return self._data.__getitem__(key)

    def __setitem__(self, key: HostKey, value: ABCHostSections) -> None:
        self._data.__setitem__(key, value)

    def __delitem__(self, key: HostKey) -> None:
        self._data.__delitem__(key)

    def __repr__(self):
        return "%s(data=%r)" % (type(self).__name__, self._data)

    def keys(self):
        return self._data.keys()  # pylint: disable=dict-keys-not-iterating

    def values(self):
        return self._data.values()  # pylint: disable=dict-values-not-iterating

    def items(self):
        return self._data.items()  # pylint: disable=dict-items-not-iterating

    def get_section_kwargs(
        self,
        host_key: HostKey,
        parsed_section_names: List[ParsedSectionName],
    ) -> Dict[str, Any]:
        """Prepares section keyword arguments for a non-cluster host

        It returns a dictionary containing one entry (may be None) for each
        of the required sections, or an empty dictionary if no data was found at all.
        """
        keys = (["section"] if len(parsed_section_names) == 1 else
                ["section_%s" % s for s in parsed_section_names])

        kwargs = {
            key: self.get_parsed_section(host_key, parsed_section_name)
            for key, parsed_section_name in zip(keys, parsed_section_names)
        }
        # empty it, if nothing was found:
        if all(v is None for v in kwargs.values()):
            kwargs.clear()

        return kwargs

    def get_section_cluster_kwargs(
        self,
        host_key: HostKey,
        parsed_section_names: List[ParsedSectionName],
        service_description: ServiceName,
    ):
        """Prepares section keyword arguments for a cluster host

        It returns a dictionary containing one optional dictionary[Host, ParsedSection]
        for each of the required sections, or an empty dictionary if no data was found at all.
        """
        # see which host entries we must use
        nodes_of_clustered_service = self._get_nodes_of_clustered_service(
            host_key.hostname, service_description) or []
        host_entries = self._get_host_entries(host_key)
        used_entries = [he for he in host_entries if he[0] in nodes_of_clustered_service]

        kwargs: Dict[str, Dict[str, Any]] = {}
        for node_key in used_entries:
            node_kwargs = self.get_section_kwargs(node_key, parsed_section_names)
            for key, sections_node_data in node_kwargs.items():
                kwargs.setdefault(key, {})[node_key.hostname] = sections_node_data
        # empty it, if nothing was found:
        if all(v is None for s in kwargs.values() for v in s.values()):
            kwargs.clear()

        return kwargs

    def get_cache_info(
        self,
        parsed_section_names: List[ParsedSectionName],
    ) -> Optional[Tuple[int, int]]:
        """Aggregate information about the age of the data in the agent sections
        """
        cached_ats: List[int] = []
        intervals: List[int] = []
        for host_key in self._data:
            for parsed_section_name in parsed_section_names:
                # Fear not, the parsing itself is cached. But in case we have not already
                # parsed, we must do so in order to see which raw sections cache info we
                # must use.
                _parsed, cache_info = self._get_parsed_section_with_cache_info(
                    host_key, parsed_section_name)
                if cache_info:
                    cached_ats.append(cache_info[0])
                    intervals.append(cache_info[1])

        return (min(cached_ats), max(intervals)) if cached_ats else None

    def get_parsed_section(
        self,
        host_key: HostKey,
        parsed_section_name: ParsedSectionName,
    ) -> Optional[ParsedSectionContent]:
        return self._get_parsed_section_with_cache_info(host_key, parsed_section_name)[0]

    def _get_parsed_section_with_cache_info(
        self,
        host_key: HostKey,
        parsed_section_name: ParsedSectionName,
    ) -> Tuple[Optional[ParsedSectionContent], Optional[Tuple[int, int]]]:
        cache_key = host_key + (parsed_section_name,)
        if cache_key in self._parsed_sections:
            return self._parsed_sections[cache_key]

        section_def = self._get_raw_section(host_key, parsed_section_name)
        if section_def is None:
            # no section creating the desired one was found, assume a 'default' section:
            raw_section_name = SectionName(str(parsed_section_name))
            parse_function: Union[SNMPParseFunction, AgentParseFunction] = parse_to_string_table
        else:
            raw_section_name = section_def.name
            parse_function = section_def.parse_function

        try:
            host_data = self._data[host_key]
            string_table = host_data.sections[raw_section_name]
            cache_info = host_data.cache_info.get(raw_section_name)
        except KeyError:
            return self._parsed_sections.setdefault(cache_key, (None, None))

        parsed = parse_function(string_table)

        return self._parsed_sections.setdefault(cache_key, (parsed, cache_info))

    def _get_raw_section(
        self,
        host_key: HostKey,
        parsed_section_name: ParsedSectionName,
    ) -> Union[AgentSectionPlugin, SNMPSectionPlugin]:
        """Get the raw sections name that will be parsed into the required section

        Raw sections may get renamed once they are parsed, if they declare it. This function
        deals with the task of determining which section we need to parse, in order to end
        up with the desired parsed section.
        This depends on the available raw sections, and thus on the host.
        """
        cache_key = host_key + (parsed_section_name,)
        if cache_key in self._parsed_to_raw_map:
            return self._parsed_to_raw_map[cache_key]

        try:
            hosts_raw_sections = self._data[host_key].sections
        except KeyError:
            return self._parsed_to_raw_map.setdefault(cache_key, None)

        section_def = agent_based_register.get_parsed_section_creator(parsed_section_name,
                                                                      list(hosts_raw_sections))
        return self._parsed_to_raw_map.setdefault(cache_key, section_def)

    def get_section_content(
            self,
            host_key: HostKey,
            management_board_info: str,
            check_plugin_name: CheckPluginNameStr,
            for_discovery: bool,
            service_description: Optional[ServiceName] = None) -> FinalSectionContent:
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

        section_name = section_name_of(check_plugin_name)
        nodes_of_clustered_service = self._get_nodes_of_clustered_service(
            host_key.hostname, service_description)
        cache_key = (host_key, management_board_info, section_name, for_discovery,
                     bool(nodes_of_clustered_service))

        try:
            return self._section_content_cache[cache_key]
        except KeyError:
            pass

        section_content = self._get_section_content(
            host_key._replace(source_type=SourceType.MANAGEMENT if management_board_info ==
                              LEGACY_MGMT_ONLY else SourceType.HOST),
            check_plugin_name,
            SectionName(section_name),
            for_discovery,
            nodes_of_clustered_service,
        )

        # If we found nothing, see if we must check the management board:
        if (section_content is None and host_key.source_type is SourceType.HOST and
                management_board_info == LEGACY_HOST_PRECEDENCE):
            section_content = self._get_section_content(
                host_key._replace(source_type=SourceType.MANAGEMENT),
                check_plugin_name,
                SectionName(section_name),
                for_discovery,
                nodes_of_clustered_service,
            )

        self._section_content_cache[cache_key] = section_content
        return section_content

    def _get_nodes_of_clustered_service(
        self,
        hostname: HostName,
        service_description: Optional[ServiceName],
    ) -> Optional[List[HostName]]:
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
            return None

        host_config = self._config_cache.get_host_config(hostname)
        nodes = host_config.nodes

        if nodes is None:
            return None

        return [
            nodename for nodename in nodes
            if hostname == self._config_cache.host_of_clustered_service(
                nodename, service_description)
        ]

    def _get_section_content(
        self,
        host_key: HostKey,
        check_plugin_name: CheckPluginNameStr,
        section_name: SectionName,
        for_discovery: bool,
        nodes_of_clustered_service: Optional[List[HostName]],
    ) -> Union[None, ParsedSectionContent, List[ParsedSectionContent]]:
        # Now get the section_content from the required hosts and merge them together to
        # a single section_content. For each host optionally add the node info.
        section_content: Optional[AbstractSectionContent] = None
        for node_key in self._get_host_entries(host_key):
            if nodes_of_clustered_service and node_key.hostname not in nodes_of_clustered_service:
                continue

            try:
                host_section_content = self._data[node_key].sections[section_name]
            except KeyError:
                continue

            host_section_content = self._update_with_node_column(
                host_section_content,
                check_plugin_name,
                node_key.hostname,
                for_discovery,
            )

            if section_content is None:
                section_content = host_section_content[:]
            else:
                section_content += host_section_content

        if section_content is None:
            return None

        assert isinstance(section_content, list)

        section_content = self._update_with_parse_function(section_content, section_name)
        section_contents = self._update_with_extra_sections(
            host_key,
            section_content,
            LEGACY_MGMT_ONLY if host_key.source_type is SourceType.MANAGEMENT else LEGACY_HOST_ONLY,
            section_name,
            for_discovery,
        )
        return section_contents

    def _get_host_entries(self, host_key: HostKey) -> List[HostKey]:
        host_config = self._config_cache.get_host_config(host_key.hostname)
        if host_config.nodes is None:
            return [host_key]

        return [
            HostKey(hostname,
                    ip_lookup.lookup_ip_address(self._config_cache.get_host_config(hostname)),
                    host_key.source_type) for hostname in host_config.nodes
        ]

    def _update_with_extra_sections(
        self,
        host_key: HostKey,
        section_content: ParsedSectionContent,
        management_board_info: str,
        section_name: SectionName,
        for_discovery: bool,
    ) -> Union[ParsedSectionContent, List[ParsedSectionContent]]:
        """Adds additional agent sections to the section_content the check receives.

        Please note that this is not a check/subcheck individual setting. This option is related
        to the agent section.
        """
        extra_sections = config.check_info.get(str(section_name), {}).get("extra_sections", [])
        if not extra_sections:
            return section_content

        # In case of extra_sections the existing info is wrapped into a new list to which all
        # extra sections are appended
        return [section_content] + [
            self.get_section_content(
                host_key,
                management_board_info,
                extra_section_name,
                for_discovery,
            ) for extra_section_name in extra_sections
        ]

    @staticmethod
    def _update_with_node_column(section_content: AbstractSectionContent,
                                 check_plugin_name: CheckPluginNameStr, hostname: HostName,
                                 for_discovery: bool) -> AbstractSectionContent:
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

        node_name: Optional[HostName] = None
        if not for_discovery and config.get_config_cache().clusters_of(hostname):
            node_name = hostname

        return MultiHostSections._add_node_column(section_content, node_name)

    # TODO: Add correct type hint for node wrapped SectionContent. We would have to create some kind
    # of AbstractSectionContentWithNodeInfo.
    @staticmethod
    def _add_node_column(
        section_content: AbstractSectionContent,
        nodename: Optional[HostName],
    ) -> AbstractSectionContent:
        new_section_content = []
        node_text = str(nodename) if isinstance(nodename, str) else nodename
        for line in section_content:
            if len(line) > 0 and isinstance(line[0], list):
                new_entry = []
                for entry in line:
                    new_entry.append([node_text] + entry)  # type: ignore[operator]
                new_section_content.append(new_entry)
            else:
                new_section_content.append([node_text] + line)  # type: ignore[arg-type,operator]
        return new_section_content  # type: ignore[return-value]

    @staticmethod
    def _update_with_parse_function(
        section_content: AbstractSectionContent,
        section_name: SectionName,
    ) -> ParsedSectionContent:
        """Transform the section_content using the defined parse functions.

        Some checks define a parse function that is used to transform the section_content
        somehow. It is applied by this function.

        Please note that this is not a check/subcheck individual setting. This option is related
        to the agent section.

        All exceptions raised by the parse function will be catched and re-raised as
        MKParseFunctionError() exceptions."""
        section_plugin = agent_based_register.get_section_plugin(section_name)
        if section_plugin is None:
            # use legacy parse function for unmigrated sections
            parse_function = config.check_info.get(str(section_name), {}).get("parse_function")
            if parse_function is None:
                return section_content
        else:
            # TODO (mo): deal with the parsed_section_name feature (CMK-4006)
            if str(section_plugin.name) != str(section_plugin.parsed_section_name):
                raise NotImplementedError()
            parse_function = section_plugin.parse_function

        # TODO (mo): make this unnecessary
        parse_function = cast(Callable[[AbstractSectionContent], ParsedSectionContent],
                              parse_function)

        # TODO: Item state needs to be handled in local objects instead of the
        # item_state._cached_item_states object
        # TODO (mo): ValueStores (formally Item state) need to be *only* available
        # from within the check function, nowhere else.
        orig_item_state_prefix = item_state.get_item_state_prefix()
        try:
            item_state.set_item_state_prefix(section_name, None)
            return parse_function(section_content)

        except item_state.MKCounterWrapped:
            raise

        except Exception:
            if cmk.utils.debug.enabled():
                raise
            raise MKParseFunctionError(*sys.exc_info())

        finally:
            item_state.set_item_state_prefix(*orig_item_state_prefix)
