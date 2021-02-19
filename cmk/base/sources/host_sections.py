#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    Dict,
    Iterator,
    List,
    MutableMapping,
    Optional,
    Set,
    Tuple,
)

import cmk.utils.caching as caching
from cmk.utils.type_defs import (
    HostKey,
    ParsedSectionName,
    SourceType,
)

from cmk.core_helpers.host_sections import HostSections

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SectionPlugin

ParsedSectionContent = Any


class ParsedSectionsBroker(MutableMapping[HostKey, HostSections]):
    """Object for aggregating, parsing and disributing the sections

    An instance of this class allocates all raw sections of a given host or cluster and
    hands over the parsed sections and caching information after considering features like
    'parsed_section_name' and 'supersedes' to all plugin functions that require this kind
    of data (inventory, discovery, checking, host_labels).
    """
    def __init__(self) -> None:
        super().__init__()
        self._data: Dict[HostKey, HostSections] = {}

        # This holds the result of the parsing of individual raw sections (by raw section name)
        self._memoized_parsing_results = caching.DictCache()
        # This holds the result of the superseding section along with the
        # cache info of the raw section that was used (by parsed section name!)
        self._memoized_parsed_sections = caching.DictCache()

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[HostKey]:
        return self._data.__iter__()

    def __getitem__(self, key: HostKey) -> HostSections:
        return self._data.__getitem__(key)

    def __setitem__(self, key: HostKey, value: HostSections) -> None:
        self._data.__setitem__(key, value)

    def __delitem__(self, key: HostKey) -> None:
        self._data.__delitem__(key)

    def __repr__(self) -> str:
        return "%s(data=%r)" % (type(self).__name__, self._data)

    # TODO (mo): consider making this a function
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

    # TODO (mo): consider making this a function
    def get_section_cluster_kwargs(
        self,
        node_keys: List[HostKey],
        parsed_section_names: List[ParsedSectionName],
    ) -> Dict[str, Dict[str, Any]]:
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
    ) -> Optional[Tuple[int, int]]:
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
    ) -> Tuple[Optional[ParsedSectionContent], Optional[Tuple[int, int]]]:
        cache_key = host_key + (parsed_section_name,)
        if cache_key in self._memoized_parsed_sections:
            return self._memoized_parsed_sections[cache_key]

        try:
            host_sections = self._data[host_key]
        except KeyError:
            return self._memoized_parsed_sections.setdefault(cache_key, (None, None))

        for section in agent_based_register.get_ranked_sections(
                host_sections.sections,
            {parsed_section_name},
        ):
            parsed = self._get_parsing_result(host_key, section)
            if parsed is None:
                continue

            cache_info = host_sections.cache_info.get(section.name)
            return self._memoized_parsed_sections.setdefault(cache_key, (parsed, cache_info))

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
        for host_key, host_sections in self._data.items():
            if host_key.source_type != source_type:
                continue

            for section in agent_based_register.get_ranked_sections(
                    host_sections.sections,
                    parse_sections,
            ):
                parsed = self._get_parsing_result(host_key, section)
                if parsed is None:
                    continue

                applicable_sections.append(section)
                self._memoized_parsed_sections[host_key + (section.parsed_section_name,)] = (
                    parsed,
                    host_sections.cache_info.get(section.name),
                )
                # set result of superseded ones to None:
                for superseded in section.supersedes:
                    self._memoized_parsing_results[host_key + (superseded,)] = None

        return applicable_sections

    def _get_parsing_result(
        self,
        host_key: HostKey,
        section: SectionPlugin,
    ) -> Any:
        # lookup the parsing result in the cache, it might have been computed
        # during resolving of the supersedings (or set to None b/c the section
        # *is* superseeded)
        cache_key = host_key + (section.name,)
        if cache_key in self._memoized_parsing_results:
            return self._memoized_parsing_results[cache_key]

        try:
            data = self._data[host_key].sections[section.name]
        except KeyError:
            return self._memoized_parsing_results.setdefault(cache_key, None)

        return self._memoized_parsing_results.setdefault(cache_key, section.parse_function(data))
