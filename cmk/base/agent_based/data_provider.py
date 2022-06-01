#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import (
    Any,
    Dict,
    Final,
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

import cmk.utils.piggyback
import cmk.utils.tty as tty
from cmk.utils.log import console
from cmk.utils.type_defs import (
    HostKey,
    HostName,
    ParsedSectionName,
    result,
    SectionName,
    SourceType,
)

import cmk.core_helpers.cache as cache
from cmk.core_helpers.host_sections import HostSections

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SectionPlugin
from cmk.base.crash_reporting import create_section_crash_dump
from cmk.base.sources.agent import AgentRawDataSection

if TYPE_CHECKING:
    from cmk.core_helpers.protocol import FetcherMessage
    from cmk.core_helpers.type_defs import SectionNameCollection

    from cmk.base.sources import Source

CacheInfo = Optional[Tuple[int, int]]

ParsedSectionContent = object  # the parse function may return *anything*.

SourceResults = Sequence[Tuple["Source", result.Result[HostSections, Exception]]]


class ParsingResult(NamedTuple):
    data: ParsedSectionContent
    cache_info: CacheInfo


class ResolvedResult(NamedTuple):
    parsed: ParsingResult
    section: SectionPlugin


class SectionsParser:
    """Call the sections parse function and return the parsing result."""

    def __init__(
        self,
        host_sections: HostSections,
        host_name: HostName,
    ) -> None:
        super().__init__()
        self._host_sections = host_sections
        self._parsing_errors: List[str] = []
        self._memoized_results: Dict[SectionName, Optional[ParsingResult]] = {}
        self._host_name = host_name

    def __repr__(self) -> str:
        return "%s(host_sections=%r, host_name=%r)" % (
            type(self).__name__,
            self._host_sections,
            self._host_name,
        )

    @property
    def parsing_errors(self) -> Sequence[str]:
        return self._parsing_errors

    def parse(self, section: SectionPlugin) -> Optional[ParsingResult]:
        if section.name in self._memoized_results:
            return self._memoized_results[section.name]

        return self._memoized_results.setdefault(
            section.name,
            None
            if (parsed := self._parse_raw_data(section)) is None
            else ParsingResult(
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

        try:
            return section.parse_function(list(raw_data))
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            self._parsing_errors.append(
                create_section_crash_dump(
                    operation="parsing",
                    section_name=section.name,
                    section_content=raw_data,
                    host_name=self._host_name,
                )
            )
            return None

    def _get_cache_info(self, section_name: SectionName) -> CacheInfo:
        return self._host_sections.cache_info.get(section_name)


class ParsedSectionsResolver:
    """Find the desired parsed data by ParsedSectionName

    This class resolves ParsedSectionNames while respecting supersedes.
    """

    def __init__(
        self,
        *,
        section_plugins: Sequence[SectionPlugin],
    ) -> None:
        self._section_plugins = section_plugins
        self._memoized_results: Dict[ParsedSectionName, Optional[ResolvedResult]] = {}
        self._superseders = self._init_superseders()
        self._producers = self._init_producers()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(section_plugins={self._section_plugins})"

    def _init_superseders(self) -> Mapping[SectionName, Sequence[SectionPlugin]]:
        superseders: Dict[SectionName, List[SectionPlugin]] = {}
        for section in self._section_plugins:
            for superseded in section.supersedes:
                superseders.setdefault(superseded, []).append(section)
        return superseders

    def _init_producers(self) -> Mapping[ParsedSectionName, Sequence[SectionPlugin]]:
        producers: Dict[ParsedSectionName, List[SectionPlugin]] = {}
        for section in self._section_plugins:
            producers.setdefault(section.parsed_section_name, []).append(section)
        return producers

    def resolve(
        self,
        parser: SectionsParser,
        parsed_section_name: ParsedSectionName,
    ) -> Optional[ResolvedResult]:
        if parsed_section_name in self._memoized_results:
            return self._memoized_results[parsed_section_name]

        # try all producers. If there can be multiple, supersedes should come into play
        for producer in self._producers.get(parsed_section_name, ()):
            # Before we can parse the section, we must parse all potential superseders.
            # Registration validates against indirect supersedings, no need to recurse
            for superseder in self._superseders.get(producer.name, ()):
                if parser.parse(superseder) is not None:
                    parser.disable(superseder.supersedes)

            if (parsing_result := parser.parse(producer)) is not None:
                return self._memoized_results.setdefault(
                    parsed_section_name,
                    ResolvedResult(
                        parsed=parsing_result,
                        section=producer,
                    ),
                )

        return self._memoized_results.setdefault(parsed_section_name, None)

    def resolve_all(self, parser: SectionsParser) -> Iterator[ResolvedResult]:
        return iter(
            res
            for psn in {section.parsed_section_name for section in self._section_plugins}
            if (res := self.resolve(parser, psn)) is not None
        )


class ParsedSectionsBroker:
    """Object for aggregating, parsing and disributing the sections

    An instance of this class allocates all raw sections of a given host or cluster and
    hands over the parsed sections and caching information after considering features like
    'parsed_section_name' and 'supersedes' to all plugin functions that require this kind
    of data (inventory, discovery, checking, host_labels).
    """

    def __init__(
        self,
        providers: Mapping[HostKey, Tuple[ParsedSectionsResolver, SectionsParser]],
    ) -> None:
        super().__init__()
        self._providers: Final = providers

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(providers={self._providers!r})"

    def get_cache_info(
        self,
        parsed_section_names: List[ParsedSectionName],
    ) -> CacheInfo:
        # TODO: should't the host key be provided here?
        """Aggregate information about the age of the data in the agent sections

        In order to determine the caching info for a parsed section we must in fact
        parse it, because otherwise we cannot know from which raw section to take
        the caching info.
        But fear not, the parsing itself is cached.
        """
        cache_infos = [
            resolved.parsed.cache_info
            for resolved in (
                resolver.resolve(parser, parsed_section_name)
                for resolver, parser in self._providers.values()
                for parsed_section_name in parsed_section_names
            )
            if resolved is not None and resolved.parsed.cache_info is not None
        ]
        return (
            (
                min(ats for ats, _intervals in cache_infos),
                max(intervals for _ats, intervals in cache_infos),
            )
            if cache_infos
            else None
        )

    def get_parsed_section(
        self,
        host_key: HostKey,
        parsed_section_name: ParsedSectionName,
    ) -> Optional[ParsedSectionContent]:
        try:
            resolver, parser = self._providers[host_key]
        except KeyError:
            return None

        return (
            None
            if (resolved := resolver.resolve(parser, parsed_section_name)) is None
            else resolved.parsed.data
        )

    def filter_available(
        self,
        parsed_section_names: Set[ParsedSectionName],
        source_type: SourceType,
    ) -> Set[ParsedSectionName]:
        return {
            parsed_section_name
            for host_key, (resolver, parser) in self._providers.items()
            for parsed_section_name in parsed_section_names
            if (
                host_key.source_type is source_type
                and resolver.resolve(parser, parsed_section_name) is not None
            )
        }

    def all_parsing_results(self, host_key: HostKey) -> Iterable[ResolvedResult]:
        try:
            resolver, parser = self._providers[host_key]
        except KeyError:
            return ()

        return sorted(resolver.resolve_all(parser), key=lambda r: r.section.name)

    def parsing_errors(self) -> Sequence[str]:
        return sum(
            (list(parser.parsing_errors) for _, parser in self._providers.values()),
            start=[],
        )


def _collect_host_sections(
    *,
    fetched: Sequence[Tuple[Source, FetcherMessage]],
    selected_sections: SectionNameCollection,
    file_cache_max_age: cache.MaxAge,
) -> Tuple[
    Mapping[HostKey, HostSections],
    Sequence[Tuple[Source, result.Result[HostSections, Exception]]],
]:
    """Gather ALL host info data for any host (hosts, nodes, clusters) in Checkmk.

    Communication errors are not raised through by this functions. All agent related errors are
    caught by the source.run() method and saved in it's _exception attribute. The caller should
    use source.get_summary_result() to get the state, output and perfdata of the agent execution
    or source.exception to get the exception object.
    """
    console.vverbose("%s+%s %s\n", tty.yellow, tty.normal, "Parse fetcher results".upper())

    collected_host_sections: Dict[HostKey, HostSections] = {}
    results: List[Tuple[Source, result.Result[HostSections, Exception]]] = []
    # Special agents can produce data for the same check_plugin_name on the same host, in this case
    # the section lines need to be extended
    for source, fetcher_message in fetched:
        console.vverbose("  Source: %s/%s\n" % (source.source_type, source.fetcher_type))

        source.file_cache_max_age = file_cache_max_age

        host_key = HostKey(source.hostname, source.source_type)
        collected_host_sections.setdefault(
            host_key,
            source.default_host_sections,
        )

        source_result = source.parse(fetcher_message.raw_data, selection=selected_sections)
        results.append((source, source_result))
        if source_result.is_ok():
            console.vverbose(
                "  -> Add sections: %s\n"
                % sorted([str(s) for s in source_result.ok.sections.keys()])
            )
            collected_host_sections[host_key] += source_result.ok
        else:
            console.vverbose("  -> Not adding sections: %s\n" % source_result.error)

    for source, _ in fetched:
        # Store piggyback information received from all sources of this host. This
        # also implies a removal of piggyback files received during previous calls.
        if source.source_type is SourceType.MANAGEMENT:
            # management board (SNMP or IPMI) does not support piggybacking
            continue
        cmk.utils.piggyback.store_piggyback_raw_data(
            source.hostname,
            collected_host_sections.setdefault(
                HostKey(source.hostname, source.source_type),
                HostSections[AgentRawDataSection](),
            ).piggybacked_raw_data,
        )

    return collected_host_sections, results


def make_broker(
    *,
    fetched: Sequence[Tuple[Source, FetcherMessage]],
    selected_sections: SectionNameCollection,
    file_cache_max_age: cache.MaxAge,
) -> Tuple[ParsedSectionsBroker, SourceResults]:
    collected_host_sections, results = _collect_host_sections(
        fetched=fetched,
        selected_sections=selected_sections,
        file_cache_max_age=file_cache_max_age,
    )
    return (
        ParsedSectionsBroker(
            {
                host_key: (
                    ParsedSectionsResolver(
                        section_plugins=[
                            agent_based_register.get_section_plugin(section_name)
                            for section_name in host_sections.sections
                        ],
                    ),
                    SectionsParser(host_sections=host_sections, host_name=host_key.hostname),
                )
                for host_key, host_sections in collected_host_sections.items()
            }
        ),
        results,
    )
