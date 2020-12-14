#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
import time
from typing import (cast, Dict, Final, Iterable, MutableMapping, NamedTuple, Optional, Tuple, List)

from six import ensure_binary, ensure_str

import cmk.utils.agent_simulator as agent_simulator
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.regex import regex, REGEX_HOST_NAME_CHARS
from cmk.utils.translations import translate_piggyback_host, TranslationOptions
from cmk.utils.type_defs import AgentRawData, AgentRawDataSection, HostName, SectionName

from ._base import Fetcher, Parser
from .cache import FileCache, FileCacheFactory, SectionStore
from .host_sections import HostSections
from .type_defs import SectionNameCollection

AgentHostSections = HostSections[AgentRawDataSection]


class AgentFileCache(FileCache[AgentRawData]):
    pass


class DefaultAgentFileCache(AgentFileCache):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        # TODO: This does not seem to be needed
        return ensure_binary(raw_data)


class NoCache(AgentFileCache):
    """Noop cache for fetchers that do not cache."""
    def read(self) -> None:
        return None

    def write(self, raw_data: AgentRawData) -> None:
        pass

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        return ensure_binary(raw_data)


class DefaultAgentFileCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> DefaultAgentFileCache:
        return DefaultAgentFileCache(
            path=self.path,
            max_age=self.max_age,
            disabled=self.disabled | self.agent_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class NoCacheFactory(FileCacheFactory[AgentRawData]):
    def make(self) -> NoCache:
        return NoCache(
            path=self.path,
            max_age=self.max_age,
            disabled=self.disabled | self.agent_disabled,
            use_outdated=self.use_outdated,
            simulation=self.simulation,
        )


class AgentFetcher(Fetcher[AgentRawData]):
    pass


class ParserState(abc.ABC):
    """Base class for the state machine.

    .. uml::

        state "NOOPState" as noop
        state "PiggybackSectionParser" as piggy
        state "HostSectionParser" as host
        state c <<choice>>

        [*] --> noop
        noop --> c

        c --> host: ""<<~<STR>>>""
        host -up-> host: ""<<~<STR>>>""
        host -> piggy: ""<<<~<STR>>>>""
        host -up-> noop: ""<<~<>>>""\nOR error

        c --> piggy : ""<<<~<STR>>>>""
        piggy --> piggy : ""<<<~<STR>>>>""
        piggy -up-> noop: ""<<<~<>>>>""\nOR error

    See Also:
        Gamma, Helm, Johnson, Vlissides (1995) Design Patterns "State pattern"

    """
    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        *,
        section_info: MutableMapping[SectionName, "HostSectionParser.Header"],
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        self.hostname: Final = hostname
        self.host_sections = host_sections
        self.section_info = section_info
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self._logger: Final = logger

    def to_noop_parser(self) -> "NOOPParser":
        return NOOPParser(
            self.hostname,
            self.host_sections,
            section_info=self.section_info,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_host_section_parser(
        self,
        section_header: "HostSectionParser.Header",
    ) -> "HostSectionParser":
        return HostSectionParser(
            self.hostname,
            self.host_sections,
            section_header,
            section_info=self.section_info,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_piggyback_section_parser(
        self,
        piggybacked_hostname: HostName,
    ) -> "PiggybackSectionParser":
        return PiggybackSectionParser(
            self.hostname,
            self.host_sections,
            piggybacked_hostname,
            section_info=self.section_info,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def __call__(self, line: bytes) -> "ParserState":
        raise NotImplementedError()


class NOOPParser(ParserState):
    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackSectionParser.is_header(line):
                piggybacked_hostname = PiggybackSectionParser.parse_header(
                    line,
                    self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self
                return self.to_piggyback_section_parser(piggybacked_hostname)
            if HostSectionParser.is_header(line):
                return self.to_host_section_parser(HostSectionParser.parse_header(line))
        except Exception:
            self._logger.warning("Ignoring invalid raw section: %r" % line, exc_info=True)
            return self.to_noop_parser()
        return self


class PiggybackSectionParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        piggybacked_hostname: HostName,
        *,
        section_info: MutableMapping[SectionName, "HostSectionParser.Header"],
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(
            hostname,
            host_sections,
            section_info=section_info,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.piggybacked_hostname: Final = piggybacked_hostname

    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackSectionParser.is_footer(line):
                return self.to_noop_parser()
            if PiggybackSectionParser.is_header(line):
                # Footer is optional.
                piggybacked_hostname = PiggybackSectionParser.parse_header(
                    line,
                    self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self.to_noop_parser()
                return self.to_piggyback_section_parser(piggybacked_hostname)
            self.host_sections.piggybacked_raw_data.setdefault(
                self.piggybacked_hostname,
                [],
            ).append(line)
        except Exception:
            self._logger.warning("Ignoring invalid raw section: %r" % line, exc_info=True)
            return self.to_noop_parser()

        return self

    @staticmethod
    def is_header(line: bytes) -> bool:
        return (line.strip().startswith(b'<<<<') and line.strip().endswith(b'>>>>') and
                not PiggybackSectionParser.is_footer(line))

    @staticmethod
    def is_footer(line: bytes) -> bool:
        return line.strip() == b'<<<<>>>>'

    @staticmethod
    def parse_header(
        line: bytes,
        translation: TranslationOptions,
        *,
        encoding_fallback: str,
    ) -> HostName:
        piggybacked_hostname = ensure_str(line.strip()[4:-4])
        assert piggybacked_hostname
        piggybacked_hostname = translate_piggyback_host(
            piggybacked_hostname,
            translation,
            encoding_fallback=encoding_fallback,
        )
        # Protect Checkmk against unallowed host names. Normally source scripts
        # like agent plugins should care about cleaning their provided host names
        # up, but we need to be sure here to prevent bugs in Checkmk code.
        return regex("[^%s]" % REGEX_HOST_NAME_CHARS).sub("_", piggybacked_hostname)


class HostSectionParser(ParserState):
    class Header(NamedTuple):
        name: SectionName
        cached: Optional[Tuple[int, int]]
        encoding: str
        nostrip: bool
        persist: Optional[int]
        separator: Optional[str]

        @classmethod
        def from_headerline(cls, headerline: bytes) -> "HostSectionParser.Header":
            def parse_options(elems: Iterable[str]) -> Iterable[Tuple[str, str]]:
                for option in elems:
                    if "(" not in option:
                        continue
                    name, value = option.split("(", 1)
                    assert value[-1] == ")", value
                    yield name, value[:-1]

            if not HostSectionParser.is_header(headerline):
                raise ValueError(headerline)

            headerparts = ensure_str(headerline[3:-3]).split(":")
            options = dict(parse_options(headerparts[1:]))
            cached: Optional[Tuple[int, int]]
            try:
                cached_ = tuple(map(int, options["cached"].split(",")))
                cached = cached_[0], cached_[1]
            except KeyError:
                cached = None

            encoding = options.get("encoding", "utf-8")
            nostrip = options.get("nostrip") is not None

            persist: Optional[int]
            try:
                persist = int(options["persist"])
            except KeyError:
                persist = None

            separator: Optional[str]
            try:
                separator = chr(int(options["sep"]))
            except KeyError:
                separator = None

            return HostSectionParser.Header(
                name=SectionName(headerparts[0]),
                cached=cached,
                encoding=encoding,
                nostrip=nostrip,
                persist=persist,
                separator=separator,
            )

        def cache_info(self, cached_at: int) -> Optional[Tuple[int, int]]:
            # If both `persist` and `cached` are present, `cached` has priority
            # over `persist`.  I do not know whether this is correct.
            if self.cached:
                return self.cached
            if self.persist is not None:
                return cached_at, self.persist - cached_at
            return None

    def __init__(
        self,
        hostname: HostName,
        host_sections: AgentHostSections,
        section_header: Header,
        *,
        section_info: MutableMapping[SectionName, "HostSectionParser.Header"],
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        host_sections.sections.setdefault(section_header.name, [])
        section_info[section_header.name] = section_header
        super().__init__(
            hostname,
            host_sections,
            section_info=section_info,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.section_header = section_header

    def __call__(self, line: bytes) -> ParserState:
        if not line.strip():
            return self

        try:
            if PiggybackSectionParser.is_header(line):
                piggybacked_hostname = PiggybackSectionParser.parse_header(
                    line,
                    self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
                if piggybacked_hostname == self.hostname:
                    # Unpiggybacked "normal" host
                    return self
                return self.to_piggyback_section_parser(piggybacked_hostname)
            if HostSectionParser.is_footer(line):
                return self.to_noop_parser()
            if HostSectionParser.is_header(line):
                # Footer is optional.
                return self.to_host_section_parser(HostSectionParser.parse_header(line))

            if not self.section_header.nostrip:
                line = line.strip()

            self.host_sections.sections[self.section_header.name].append(
                ensure_str_with_fallback(
                    line,
                    encoding=self.section_header.encoding,
                    fallback="latin-1",
                ).split(self.section_header.separator))
        except Exception:
            self._logger.warning("Ignoring invalid raw section: %r" % line, exc_info=True)
            return self.to_noop_parser()
        return self

    @staticmethod
    def is_header(line: bytes) -> bool:
        line = line.strip()
        return (line.startswith(b'<<<') and line.endswith(b'>>>') and
                not HostSectionParser.is_footer(line) and
                not PiggybackSectionParser.is_header(line) and
                not PiggybackSectionParser.is_footer(line))

    @staticmethod
    def is_footer(line: bytes) -> bool:
        return line.strip() == b'<<<>>>'

    @staticmethod
    def parse_header(line: bytes) -> Header:
        return HostSectionParser.Header.from_headerline(line)


class AgentParser(Parser[AgentRawData, AgentHostSections]):
    """A parser for agent data.

    Note:
        It is forbidden to add base dependencies to this class.

    """
    def __init__(
        self,
        hostname: HostName,
        section_store: SectionStore[AgentRawDataSection],
        *,
        check_interval: int,
        keep_outdated: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        simulation: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.check_interval: Final = check_interval
        self.section_store: Final = section_store
        self.keep_outdated: Final = keep_outdated
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self.simulation: Final = simulation
        self._logger = logger

    def parse(
        self,
        raw_data: AgentRawData,
        *,
        selection: SectionNameCollection,
    ) -> AgentHostSections:
        if self.simulation:
            raw_data = agent_simulator.process(raw_data)

        now = int(time.time())

        parser = self._parse_host_section(raw_data)

        host_sections = parser.host_sections
        # Transform to seconds and give the piggybacked host a little bit more time
        cache_age = int(1.5 * 60 * self.check_interval)
        host_sections.cache_info.update({
            header.name: cast(Tuple[int, int], header.cache_info(now))
            for header in parser.section_info.values()
            if header.cache_info(now) is not None
        })
        host_sections.piggybacked_raw_data = self._make_updated_piggyback_section_header(
            host_sections.piggybacked_raw_data,
            cached_at=now,
            cache_age=cache_age,
        )
        host_sections.add_persisted_sections(
            host_sections.sections,
            section_store=self.section_store,
            fetch_interval=lambda section_name: parser.section_info[section_name].persist,
            now=now,
            keep_outdated=self.keep_outdated,
            logger=self._logger,
        )
        return host_sections.filter(selection)

    def _parse_host_section(self, raw_data: AgentRawData) -> ParserState:
        """Split agent output in chunks, splits lines by whitespaces."""
        parser: ParserState = NOOPParser(
            self.hostname,
            AgentHostSections(),
            section_info={},
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )
        for line in raw_data.split(b"\n"):
            parser = parser(line.rstrip(b"\n"))

        return parser

    @staticmethod
    def _make_updated_piggyback_section_header(
        piggybacked_raw_data: Dict[HostName, List[bytes]],
        *,
        cached_at: int,
        cache_age: int,
    ) -> Dict[HostName, List[bytes]]:
        def update_section_header(line: bytes) -> bytes:
            """Append cache information to section headers.

            If the `line` is a section header without caching
            information, these are added to the header.
            Return any other line without modification.

            """
            if not HostSectionParser.is_header(line):
                return line
            if b':cached(' in line or b':persist(' in line:
                return line
            return b'<<<%s:cached(%s,%s)>>>' % (
                line[3:-3],
                ensure_binary("%d" % cached_at),
                ensure_binary("%d" % cache_age),
            )

        updated_piggybacked_raw_data: Dict[HostName, List[bytes]] = {}
        for hostname, raw_data in piggybacked_raw_data.items():
            updated_piggybacked_raw_data[hostname] = [
                update_section_header(line) for line in raw_data
            ]
        return updated_piggybacked_raw_data
