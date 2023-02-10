#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final, NamedTuple

import cmk.utils.piggyback
from cmk.utils.log import console
from cmk.utils.type_defs import HostName, ParsedSectionName, result, SectionName

from cmk.checkers import HostKey, SourceInfo, SourceType
from cmk.checkers.crash_reporting import create_section_crash_dump
from cmk.checkers.host_sections import HostSections

from cmk.base.api.agent_based.type_defs import AgentParseFunction, SectionPlugin, SNMPParseFunction

_CacheInfo = tuple[int, int]

ParsedSectionContent = object  # the parse function may return *anything*.


def filter_out_errors(
    host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]]
) -> Mapping[HostKey, HostSections]:
    output: dict[HostKey, HostSections] = {}
    for source, host_section in host_sections:
        host_key = HostKey(source.hostname, source.source_type)
        console.vverbose(f"  {host_key!s}")
        output.setdefault(host_key, HostSections())
        if host_section.is_ok():
            console.vverbose(
                "  -> Add sections: %s\n"
                % sorted([str(s) for s in host_section.ok.sections.keys()])
            )
            output[host_key] += host_section.ok
        else:
            console.vverbose("  -> Not adding sections: %s\n" % host_section.error)
    return output


class ParsingResult(NamedTuple):
    data: ParsedSectionContent
    cache_info: _CacheInfo | None


class ResolvedResult(NamedTuple):
    parsed: ParsingResult
    section: SectionPlugin


class SectionParser(NamedTuple):
    section_name: SectionName
    parse: AgentParseFunction | SNMPParseFunction


class SectionsParser:
    """Call the sections parse function and return the parsing result."""

    def __init__(
        self,
        host_sections: HostSections,
        host_name: HostName,
    ) -> None:
        super().__init__()
        self._host_sections = host_sections
        self._parsing_errors: list[str] = []
        self._memoized_results: dict[SectionName, ParsingResult | None] = {}
        self._host_name = host_name

    def __repr__(self) -> str:
        return "{}(host_sections={!r}, host_name={!r})".format(
            type(self).__name__,
            self._host_sections,
            self._host_name,
        )

    @property
    def parsing_errors(self) -> Sequence[str]:
        return self._parsing_errors

    def parse(self, section_parser: SectionParser) -> ParsingResult | None:
        if section_parser.section_name in self._memoized_results:
            return self._memoized_results[section_parser.section_name]

        return self._memoized_results.setdefault(
            section_parser.section_name,
            None
            if (parsed := self._parse_raw_data(section_parser)) is None
            else ParsingResult(
                data=parsed,
                cache_info=self._get_cache_info(section_parser.section_name),
            ),
        )

    def disable(self, raw_section_names: Iterable[SectionName]) -> None:
        for section_name in raw_section_names:
            self._memoized_results[section_name] = None

    def _parse_raw_data(self, section_parser: SectionParser) -> Any:  # yes *ANY*
        try:
            raw_data = self._host_sections.sections[section_parser.section_name]
        except KeyError:
            return None

        try:
            return section_parser.parse(list(raw_data))
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            self._parsing_errors.append(
                create_section_crash_dump(
                    operation="parsing",
                    section_name=section_parser.section_name,
                    section_content=raw_data,
                    host_name=self._host_name,
                    rtc_package=None,
                )
            )
            return None

    def _get_cache_info(self, section_name: SectionName) -> _CacheInfo | None:
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
        self.section_plugins: Final = section_plugins
        self._superseders = ParsedSectionsResolver._init_superseders(section_plugins)
        self._producers = ParsedSectionsResolver._init_producers(section_plugins)
        self._memoized_results: dict[ParsedSectionName, ResolvedResult | None] = {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(section_plugins={self.section_plugins})"

    @staticmethod
    def _init_superseders(
        section_plugins: Iterable[SectionPlugin],
    ) -> Mapping[SectionName, Sequence[SectionPlugin]]:
        superseders: dict[SectionName, list[SectionPlugin]] = {}
        for section in section_plugins:
            for superseded in section.supersedes:
                superseders.setdefault(superseded, []).append(section)
        return superseders

    @staticmethod
    def _init_producers(
        section_plugins: Iterable[SectionPlugin],
    ) -> Mapping[ParsedSectionName, Sequence[SectionPlugin]]:
        producers: dict[ParsedSectionName, list[SectionPlugin]] = {}
        for section in section_plugins:
            producers.setdefault(section.parsed_section_name, []).append(section)
        return producers

    def resolve(
        self,
        parser: SectionsParser,
        parsed_section_name: ParsedSectionName,
    ) -> ResolvedResult | None:
        if parsed_section_name in self._memoized_results:
            return self._memoized_results[parsed_section_name]

        # try all producers. If there can be multiple, supersedes should come into play
        for producer in self._producers.get(parsed_section_name, ()):
            # Before we can parse the section, we must parse all potential superseders.
            # Registration validates against indirect supersedings, no need to recurse
            for superseder in self._superseders.get(producer.name, ()):
                if (
                    parser.parse(SectionParser(superseder.name, superseder.parse_function))
                    is not None
                ):
                    parser.disable(superseder.supersedes)

            if (
                parsing_result := parser.parse(
                    SectionParser(producer.name, producer.parse_function)
                )
            ) is not None:
                return self._memoized_results.setdefault(
                    parsed_section_name,
                    ResolvedResult(
                        parsed=parsing_result,
                        section=producer,
                    ),
                )

        return self._memoized_results.setdefault(parsed_section_name, None)


class ParsedSectionsBroker:
    """Object for aggregating, parsing and disributing the sections

    An instance of this class allocates all raw sections of a given host or cluster and
    hands over the parsed sections and caching information after considering features like
    'parsed_section_name' and 'supersedes' to all plugin functions that require this kind
    of data (inventory, discovery, checking, host_labels).
    """

    def __init__(
        self,
        providers: Mapping[HostKey, tuple[ParsedSectionsResolver, SectionsParser]],
    ) -> None:
        super().__init__()
        self.providers: Final = providers

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(providers={self.providers!r})"

    def get_cache_info(
        self,
        parsed_section_names: list[ParsedSectionName],
    ) -> _CacheInfo | None:
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
                for resolver, parser in self.providers.values()
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
    ) -> ParsedSectionContent | None:
        try:
            resolver, parser = self.providers[host_key]
        except KeyError:
            return None

        return (
            None
            if (resolved := resolver.resolve(parser, parsed_section_name)) is None
            else resolved.parsed.data
        )

    def filter_available(
        self,
        parsed_section_names: Iterable[ParsedSectionName],
        source_type: SourceType,
    ) -> set[ParsedSectionName]:
        return {
            parsed_section_name
            for host_key, (resolver, parser) in self.providers.items()
            for parsed_section_name in parsed_section_names
            if (
                host_key.source_type is source_type
                and resolver.resolve(parser, parsed_section_name) is not None
            )
        }

    def parsing_errors(self) -> Sequence[str]:
        return sum(
            (list(parser.parsing_errors) for _, parser in self.providers.values()),
            start=[],
        )


def store_piggybacked_sections(collected_host_sections: Mapping[HostKey, HostSections]) -> None:
    for host_key, host_sections in collected_host_sections.items():
        # Store piggyback information received from all sources of this host. This
        # also implies a removal of piggyback files received during previous calls.
        if host_key.source_type is SourceType.MANAGEMENT:
            # management board (SNMP or IPMI) does not support piggybacking
            continue

        cmk.utils.piggyback.store_piggyback_raw_data(
            host_key.hostname, host_sections.piggybacked_raw_data
        )


def make_broker(
    host_sections: Mapping[HostKey, HostSections],
    section_plugins: Mapping[SectionName, SectionPlugin],
) -> ParsedSectionsBroker:
    return ParsedSectionsBroker(
        {
            host_key: (
                ParsedSectionsResolver(
                    section_plugins=[
                        section_plugins[section_name] for section_name in host_sections.sections
                    ],
                ),
                SectionsParser(host_sections=host_sections, host_name=host_key.hostname),
            )
            for host_key, host_sections in host_sections.items()
        }
    )
