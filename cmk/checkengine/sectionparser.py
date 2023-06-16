#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Container, Iterable, Mapping, Sequence, Set
from dataclasses import dataclass
from typing import Any, Final, Generic, NamedTuple

import cmk.utils.piggyback
import cmk.utils.resulttype as result
from cmk.utils.hostaddress import HostName
from cmk.utils.log import console
from cmk.utils.sectionname import SectionName
from cmk.utils.validatedstr import ValidatedString

from ._typedefs import HostKey, SourceInfo, SourceType
from .crash_reporting import create_section_crash_dump
from .host_sections import HostSections, TRawDataSection

_CacheInfo = tuple[int, int]

ParsedSectionContent = object  # the parse function may return *anything*.


class ParsedSectionName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        return super().exceptions()


@dataclass(frozen=True)
class SectionPlugin:
    supersedes: Set[SectionName]
    # This function isn't typed precisely in the Check API.  Let's just
    # keep the smallest common type of all the unions defined over there.
    parse_function: Callable[..., object]
    parsed_section_name: ParsedSectionName


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


class _ParsingResult(NamedTuple):
    data: ParsedSectionContent
    cache_info: _CacheInfo | None


class ResolvedResult(NamedTuple):
    section_name: SectionName
    parsed_data: ParsedSectionContent
    cache_info: _CacheInfo | None


class SectionsParser(Generic[TRawDataSection]):
    """Call the sections parse function and return the parsing result."""

    def __init__(
        self,
        host_sections: HostSections[TRawDataSection],
        host_name: HostName,
    ) -> None:
        super().__init__()
        self._host_sections: HostSections[TRawDataSection] = host_sections
        self.parsing_errors: list[str] = []
        self._memoized_results: dict[SectionName, _ParsingResult | None] = {}
        self._host_name = host_name

    def __repr__(self) -> str:
        return "{}(host_sections={!r}, host_name={!r})".format(
            type(self).__name__,
            self._host_sections,
            self._host_name,
        )

    def parse(
        self, section_name: SectionName, parse_function: Callable[[Sequence[TRawDataSection]], Any]
    ) -> _ParsingResult | None:
        if section_name in self._memoized_results:
            return self._memoized_results[section_name]

        return self._memoized_results.setdefault(
            section_name,
            None
            if (parsed := self._parse_raw_data(section_name, parse_function)) is None
            else _ParsingResult(
                data=parsed,
                cache_info=self._host_sections.cache_info.get(section_name),
            ),
        )

    def disable(self, raw_section_names: Iterable[SectionName]) -> None:
        for section_name in raw_section_names:
            self._memoized_results[section_name] = None

    def _parse_raw_data(
        self, section_name: SectionName, parse_function: Callable[[Sequence[TRawDataSection]], Any]
    ) -> Any:  # yes *ANY*
        try:
            raw_data = self._host_sections.sections[section_name]
        except KeyError:
            return None

        try:
            return parse_function(list(raw_data))
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            self.parsing_errors.append(
                create_section_crash_dump(
                    operation="parsing",
                    section_name=section_name,
                    section_content=raw_data,
                    host_name=self._host_name,
                    rtc_package=None,
                )
            )
            return None


class ParsedSectionsResolver:
    """Find the desired parsed data by ParsedSectionName

    This class resolves ParsedSectionNames while respecting supersedes.
    """

    def __init__(
        self,
        parser: SectionsParser,
        *,
        section_plugins: Mapping[SectionName, SectionPlugin],
    ) -> None:
        self._parser: Final = parser
        self.section_plugins: Final = section_plugins
        self._superseders = ParsedSectionsResolver._init_superseders(section_plugins)
        self._producers = ParsedSectionsResolver._init_producers(section_plugins)
        self._memoized_results: dict[ParsedSectionName, ResolvedResult | None] = {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(section_plugins={self.section_plugins})"

    @property
    def parsing_errors(self) -> Sequence[str]:
        return self._parser.parsing_errors

    @staticmethod
    def _init_superseders(
        section_plugins: Mapping[SectionName, SectionPlugin],
    ) -> Mapping[SectionName, Sequence[tuple[SectionName, SectionPlugin]]]:
        superseders: dict[SectionName, list[tuple[SectionName, SectionPlugin]]] = {}
        for section_name, section in section_plugins.items():
            for superseded in section.supersedes:
                superseders.setdefault(superseded, []).append((section_name, section))
        return superseders

    @staticmethod
    def _init_producers(
        section_plugins: Mapping[SectionName, SectionPlugin],
    ) -> Mapping[ParsedSectionName, Sequence[tuple[SectionName, SectionPlugin]]]:
        producers: dict[ParsedSectionName, list[tuple[SectionName, SectionPlugin]]] = {}
        for section_name, section in section_plugins.items():
            producers.setdefault(section.parsed_section_name, []).append((section_name, section))
        return producers

    def resolve(
        self,
        parsed_section_name: ParsedSectionName,
    ) -> ResolvedResult | None:
        if parsed_section_name in self._memoized_results:
            return self._memoized_results[parsed_section_name]

        # try all producers. If there can be multiple, supersedes should come into play
        for producer_name, producer in self._producers.get(parsed_section_name, ()):
            # Before we can parse the section, we must parse all potential superseders.
            # Registration validates against indirect supersedings, no need to recurse
            for superseder_name, superseder in self._superseders.get(producer_name, ()):
                if self._parser.parse(superseder_name, superseder.parse_function) is not None:
                    self._parser.disable(superseder.supersedes)

            if (
                parsing_result := self._parser.parse(producer_name, producer.parse_function)
            ) is not None:
                return self._memoized_results.setdefault(
                    parsed_section_name,
                    ResolvedResult(
                        section_name=producer_name,
                        parsed_data=parsing_result.data,
                        cache_info=parsing_result.cache_info,
                    ),
                )

        return self._memoized_results.setdefault(parsed_section_name, None)


Provider = ParsedSectionsResolver


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


def make_providers(
    host_sections: Mapping[HostKey, HostSections],
    section_plugins: Mapping[SectionName, SectionPlugin],
) -> Mapping[HostKey, Provider]:
    return {
        host_key: ParsedSectionsResolver(
            SectionsParser(host_sections=host_sections, host_name=host_key.hostname),
            section_plugins={
                section_name: section_plugins[section_name]
                for section_name in host_sections.sections
            },
        )
        for host_key, host_sections in host_sections.items()
    }
