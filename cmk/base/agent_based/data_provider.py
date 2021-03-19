#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    TYPE_CHECKING,
)

import cmk.utils.caching as caching
from cmk.utils.log import console
import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    HostKey,
    ParsedSectionName,
    result,
    SectionName,
    SourceType,
)

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SectionPlugin
from cmk.base.sources import fetch_all, make_nodes, make_sources
from cmk.base.sources.agent import AgentHostSections
from cmk.core_helpers.host_sections import HostSections

if TYPE_CHECKING:
    from cmk.base.sources import Source
    from cmk.base.config import ConfigCache, HostConfig
    from cmk.core_helpers.protocol import FetcherMessage
    from cmk.core_helpers.type_defs import Mode, SectionNameCollection

CacheInfo = Optional[Tuple[int, int]]

ParsedSectionContent = Any


class ParsingResult(NamedTuple):
    data: ParsedSectionContent
    cache_info: CacheInfo


class SectionsParser:
    """Call the sections parse function and return the parsing result.
    """
    def __init__(
        self,
        host_sections: HostSections,
    ) -> None:
        super().__init__()
        self._host_sections = host_sections
        self._memoized_results: Dict[SectionName, Optional[ParsingResult]] = {}

    def __repr__(self) -> str:
        return "%s(host_sections=%r)" % (type(self).__name__, self._host_sections)

    @property
    def raw_data(self):  # This is needed for the legacy mode from hell :-(. Remove ASAP
        return self._host_sections

    @property
    def sections(self) -> Iterable[SectionName]:  # TODO: see if we really need this in the long run
        return self._host_sections.sections.keys()

    def parse(self, section: SectionPlugin) -> Optional[ParsingResult]:
        if section.name in self._memoized_results:
            return self._memoized_results[section.name]

        return self._memoized_results.setdefault(
            section.name,
            None if (parsed := self._parse_raw_data(section)) is None else ParsingResult(
                data=parsed,
                cache_info=self._get_cache_info(section.name),
            ),
        )

    def disable(self, raw_section_names: Iterable[SectionName]) -> None:
        for section_name in raw_section_names:
            self._memoized_results[section_name] = None

    def _parse_raw_data(self, section: SectionPlugin) -> Any:  # yes *ANY*
        try:
            raw_data = self._host_sections.sections[section.name]
        except KeyError:
            return None
        return section.parse_function(raw_data)

    def _get_cache_info(self, section_name: SectionName) -> CacheInfo:
        return self._host_sections.cache_info.get(section_name)


class ParsedSectionsBroker(Mapping[HostKey, SectionsParser]):
    """Object for aggregating, parsing and disributing the sections

    An instance of this class allocates all raw sections of a given host or cluster and
    hands over the parsed sections and caching information after considering features like
    'parsed_section_name' and 'supersedes' to all plugin functions that require this kind
    of data (inventory, discovery, checking, host_labels).
    """
    def __init__(
        self,
        data: Mapping[HostKey, HostSections],
    ) -> None:
        super().__init__()
        # TODO: rename _data
        self._data = {
            host_key: SectionsParser(host_sections=host_sections)
            for host_key, host_sections in data.items()
        }

        # This holds the result of the superseding section along with the
        # cache info of the raw section that was used (by parsed section name!)
        self._memoized_parsed_sections = caching.DictCache()

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[HostKey]:
        return self._data.__iter__()

    def __getitem__(self, key: HostKey) -> SectionsParser:
        return self._data.__getitem__(key)

    def __repr__(self) -> str:
        return "%s(data=%r)" % (type(self).__name__, self._data)

    # TODO (mo): consider making this a function
    def get_section_kwargs(
        self,
        host_key: HostKey,
        parsed_section_names: List[ParsedSectionName],
    ) -> Dict[str, ParsedSectionContent]:
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

    # TODO (mo): consider making this a function
    def get_section_cluster_kwargs(
        self,
        node_keys: List[HostKey],
        parsed_section_names: List[ParsedSectionName],
    ) -> Dict[str, Dict[str, ParsedSectionContent]]:
        """Prepares section keyword arguments for a cluster host

        It returns a dictionary containing one optional dictionary[Host, ParsedSection]
        for each of the required sections, or an empty dictionary if no data was found at all.
        """
        kwargs: Dict[str, Dict[str, Any]] = {}
        for node_key in node_keys:
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
    ) -> CacheInfo:
        """Aggregate information about the age of the data in the agent sections

        In order to determine the caching info for a parsed section we must in fact
        parse it, because otherwise we cannot know from which raw section to take
        the caching info.
        But fear not, the parsing itself is cached.
        """
        cache_infos = [
            cache_info  #
            for _parsed, cache_info in (  #
                self._get_parsed_section_with_cache_info(host_key, parsed_section_name)
                for host_key in self._data
                for parsed_section_name in parsed_section_names  #
            )  #
            if cache_info
        ]
        return (
            min(ats for ats, _intervals in cache_infos),
            max(intervals for _ats, intervals in cache_infos),
        ) if cache_infos else None

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
    ) -> Tuple[Optional[ParsedSectionContent], CacheInfo]:
        cache_key = host_key + (parsed_section_name,)
        if cache_key in self._memoized_parsed_sections:
            return self._memoized_parsed_sections[cache_key]

        try:
            sections_parser = self._data[host_key]
        except KeyError:
            return self._memoized_parsed_sections.setdefault(cache_key, (None, None))

        for section in agent_based_register.get_ranked_sections(
                sections_parser.sections,
            {parsed_section_name},
        ):
            parsing_result = sections_parser.parse(section)
            if parsing_result is None:
                continue
            return self._memoized_parsed_sections.setdefault(
                cache_key, (parsing_result.data, parsing_result.cache_info))

        return self._memoized_parsed_sections.setdefault(cache_key, (None, None))

    def determine_applicable_sections(
        self,
        parse_sections: Set[ParsedSectionName],
        source_type: SourceType,
    ) -> List[SectionPlugin]:
        """Try to parse all given sections and return a set of names for which the
        parsed sections value is not None.

        This takes into account the supersedings and permanently "dismisses" all
        superseded raw sections (by setting their parsing result to None).
        """
        applicable_sections: List[SectionPlugin] = []
        for host_key, sections_parser in self._data.items():
            if host_key.source_type != source_type:
                continue

            for section in agent_based_register.get_ranked_sections(
                    sections_parser.sections,
                    parse_sections,
            ):
                parsing_result = sections_parser.parse(section)
                if parsing_result is None:
                    continue

                applicable_sections.append(section)
                self._memoized_parsed_sections[host_key +
                                               (section.parsed_section_name,)] = parsing_result
                # disable superseded sections:
                sections_parser.disable(section.supersedes)

        return applicable_sections


def _collect_host_sections(
    *,
    nodes: Iterable[Tuple[HostName, Optional[HostAddress], Sequence['Source']]],
    file_cache_max_age: int,
    fetcher_messages: Sequence['FetcherMessage'],
    selected_sections: 'SectionNameCollection',
) -> Tuple[  #
        Mapping[HostKey, HostSections],  #
        Sequence[Tuple['Source', result.Result[HostSections, Exception]]]  #
]:
    """Gather ALL host info data for any host (hosts, nodes, clusters) in Checkmk.

    Communication errors are not raised through by this functions. All agent related errors are
    caught by the source.run() method and saved in it's _exception attribute. The caller should
    use source.get_summary_result() to get the state, output and perfdata of the agent execution
    or source.exception to get the exception object.
    """
    console.vverbose("%s+%s %s\n", tty.yellow, tty.normal, "Parse fetcher results".upper())

    flat_node_sources = [(hn, ip, src) for hn, ip, sources in nodes for src in sources]

    # TODO (ml): Can we somehow verify that this is correct?
    # if fetcher_message["fetcher_type"] != source.id:
    #     raise LookupError("Checker and fetcher missmatch")
    # (mo): this is not enough, but better than nothing:
    if len(flat_node_sources) != len(fetcher_messages):
        raise LookupError("Checker and fetcher missmatch")

    collected_host_sections: Dict[HostKey, HostSections] = {}
    results: List[Tuple['Source', result.Result[HostSections, Exception]]] = []
    # Special agents can produce data for the same check_plugin_name on the same host, in this case
    # the section lines need to be extended
    for fetcher_message, (hostname, ipaddress, source) in zip(fetcher_messages, flat_node_sources):
        console.vverbose("  Source: %s/%s\n" % (source.source_type, source.fetcher_type))

        source.file_cache_max_age = file_cache_max_age

        host_sections = collected_host_sections.setdefault(
            HostKey(hostname, ipaddress, source.source_type),
            source.default_host_sections,
        )

        source_result = source.parse(fetcher_message.raw_data, selection=selected_sections)
        results.append((source, source_result))
        if source_result.is_ok():
            console.vverbose("  -> Add sections: %s\n" %
                             sorted([str(s) for s in source_result.ok.sections.keys()]))
            host_sections.add(source_result.ok)
        else:
            console.vverbose("  -> Not adding sections: %s\n" % source_result.error)

    for hostname, ipaddress, _sources in nodes:
        # Store piggyback information received from all sources of this host. This
        # also implies a removal of piggyback files received during previous calls.
        host_sections = collected_host_sections.setdefault(
            HostKey(hostname, ipaddress, SourceType.HOST),
            AgentHostSections(),
        )
        cmk.utils.piggyback.store_piggyback_raw_data(
            hostname,
            host_sections.piggybacked_raw_data,
        )

    return collected_host_sections, results


def make_broker(
    *,
    config_cache: 'ConfigCache',
    host_config: 'HostConfig',
    ip_address: Optional[HostAddress],
    mode: 'Mode',
    selected_sections: 'SectionNameCollection',
    file_cache_max_age: int,
    fetcher_messages: Sequence['FetcherMessage'],
    force_snmp_cache_refresh: bool,
    on_scan_error: str,
) -> Tuple[ParsedSectionsBroker, Sequence[Tuple['Source', result.Result[HostSections, Exception]]]]:
    nodes = make_nodes(
        config_cache,
        host_config,
        ip_address,
        mode,
        make_sources(
            host_config,
            ip_address,
            mode=mode,
            selected_sections=selected_sections,
            force_snmp_cache_refresh=force_snmp_cache_refresh,
            on_scan_error=on_scan_error,
        ),
    )

    if not fetcher_messages:
        # Note: *Not* calling `fetch_all(sources)` here is probably buggy.
        # Note: `fetch_all(sources)` is almost always called in similar
        #       code in discovery and inventory.  The only two exceptions
        #       are `cmk.base.checking.do_check(...)` and
        #       `cmk.base.discovery.check_discovery(...)`.
        #       This does not seem right.
        fetcher_messages = list(fetch_all(
            nodes=nodes,
            file_cache_max_age=file_cache_max_age,
        ))

    collected_host_sections, results = _collect_host_sections(
        nodes=nodes,
        file_cache_max_age=file_cache_max_age,
        fetcher_messages=fetcher_messages,
        selected_sections=selected_sections,
    )
    return ParsedSectionsBroker(collected_host_sections), results
