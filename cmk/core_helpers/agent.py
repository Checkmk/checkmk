#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import logging
import os
import time
from pathlib import Path
from typing import (
    final,
    Final,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import cmk.utils.agent_simulator as agent_simulator
import cmk.utils.debug
import cmk.utils.misc
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import AgentRawData, HostName, SectionName

from ._base import Fetcher, Parser, Summarizer
from ._markers import PiggybackMarker, SectionMarker
from .cache import FileCache, FileCacheFactory, MaxAge, SectionStore
from .host_sections import HostSections
from .type_defs import AgentRawDataSection, Mode, NO_SELECTION, SectionNameCollection


class AgentFileCache(FileCache[AgentRawData]):
    pass


class DefaultAgentFileCache(AgentFileCache):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        # TODO: This does not seem to be needed
        return raw_data

    def make_path(self, mode: Mode) -> Path:
        return self.base_path / self.hostname


class NoCache(AgentFileCache):
    """Noop cache for fetchers that do not cache."""

    def __init__(
        self,
        hostname: HostName,
        *,
        base_path: Union[str, Path],
        max_age: MaxAge,
        disabled: bool,
        use_outdated: bool,
        simulation: bool,
    ) -> None:
        # Force disable
        disabled = True
        super().__init__(
            hostname,
            base_path=base_path,
            max_age=max_age,
            disabled=disabled,
            use_outdated=use_outdated,
            simulation=simulation,
        )

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> AgentRawData:
        return AgentRawData(raw_data)

    @staticmethod
    def _to_cache_file(raw_data: AgentRawData) -> bytes:
        return raw_data

    def make_path(self, mode: Mode):
        return Path(os.devnull)


class DefaultAgentFileCacheFactory(FileCacheFactory[AgentRawData]):
    # force_cache_refresh is currently only used by SNMP. It's probably less irritating
    # to implement it here anyway:
    def make(self, *, force_cache_refresh: bool = False) -> DefaultAgentFileCache:
        return DefaultAgentFileCache(
            self.hostname,
            base_path=self.base_path,
            max_age=MaxAge.none() if force_cache_refresh else self.max_age,
            disabled=self.disabled,
            use_outdated=False if force_cache_refresh else self.use_outdated,
            simulation=self.simulation,
        )


class NoCacheFactory(FileCacheFactory[AgentRawData]):
    # force_cache_refresh is currently only used by SNMP. It's probably less irritating
    # to implement it here anyway. At the time of this writing NoCache does nothing either way.
    def make(self, *, force_cache_refresh: bool = False) -> NoCache:
        return NoCache(
            self.hostname,
            base_path=self.base_path,
            max_age=MaxAge.none() if force_cache_refresh else self.max_age,
            disabled=self.disabled,
            use_outdated=False if force_cache_refresh else self.use_outdated,
            simulation=self.simulation,
        )


class AgentFetcher(Fetcher[AgentRawData]):
    pass


MutableSection = MutableMapping[SectionMarker, List[AgentRawData]]
ImmutableSection = Mapping[SectionMarker, Sequence[AgentRawData]]


class ParserState(abc.ABC):
    """Base class for the state machine.

    .. uml::

        state Host {
            state "NOOP" as hnoop
            state "Host Section" as hsection
            [*] --> hnoop
        }

        state PiggybackedHost {
            state "Piggybacked Host" as phost
            state "Piggybacked Host NOOP" as pnoop
            state "Piggybacked Host Section" as psection
            [*] --> phost
        }

        [*] --> Host
        hnoop --> hsection : ""<<~<SECTION_NAME>>>""
        hsection --> hsection : ""<<~<SECTION_NAME>>>""
        hsection --> hnoop : ""<<~<>>>""

        phost --> pnoop : ""<<~<>>>""
        phost --> psection : ""<<~<SECTION_NAME>>>""
        psection --> psection : ""<<~<SECTION_NAME>>>""
        psection --> pnoop : ""<<~<>>>""

        Host --> PiggybackedHost : ""<<<~<HOSTNAME>>>>""
        PiggybackedHost --> Host : ""<<<~<>>>>""
        Host --> Host : ""<<<~<>>>>""
        PiggybackedHost --> PiggybackedHost : ""<<<~<HOSTNAME>>>>""

    See Also:
        Gamma, Helm, Johnson, Vlissides (1995) Design Patterns "State pattern"

    """

    def __init__(
        self,
        hostname: HostName,
        sections: MutableSection,
        piggyback_sections: MutableMapping[PiggybackMarker, MutableSection],
        *,
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        self.hostname: Final = hostname
        self.sections = sections
        self.piggyback_sections = piggyback_sections
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self._logger: Final = logger

    @abc.abstractmethod
    def do_action(self, line: bytes) -> "ParserState":
        raise NotImplementedError()

    @abc.abstractmethod
    def on_section_header(self, line: bytes) -> "ParserState":
        raise NotImplementedError()

    @abc.abstractmethod
    def on_section_footer(self, line: bytes) -> "ParserState":
        raise NotImplementedError()

    @abc.abstractmethod
    def on_piggyback_header(self, line: bytes) -> "ParserState":
        raise NotImplementedError()

    @abc.abstractmethod
    def on_piggyback_footer(self, line: bytes) -> "ParserState":
        raise NotImplementedError()

    def to_noop_parser(self) -> "NOOPParser":
        self._logger.debug("Transition %s -> %s", type(self).__name__, NOOPParser.__name__)
        return NOOPParser(
            self.hostname,
            self.sections,
            self.piggyback_sections,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_host_section_parser(
        self,
        section_header: SectionMarker,
    ) -> "HostSectionParser":
        self._logger.debug(
            "%s / Transition %s -> %s",
            section_header,
            type(self).__name__,
            HostSectionParser.__name__,
        )
        self.sections.setdefault(section_header, [])
        return HostSectionParser(
            self.hostname,
            self.sections,
            self.piggyback_sections,
            current_section=section_header,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_piggyback_parser(
        self,
        header: PiggybackMarker,
    ) -> "PiggybackParser":
        self._logger.debug(
            "%s / Transition %s -> %s",
            header,
            type(self).__name__,
            PiggybackParser.__name__,
        )
        self.piggyback_sections.setdefault(header, {})
        return PiggybackParser(
            self.hostname,
            self.sections,
            self.piggyback_sections,
            current_host=header,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_piggyback_section_parser(
        self,
        current_host: PiggybackMarker,
        section_header: SectionMarker,
    ) -> "PiggybackSectionParser":
        self._logger.debug(
            "%r %r / Transition %s -> %s",
            current_host,
            section_header,
            type(self).__name__,
            PiggybackSectionParser.__name__,
        )
        self.piggyback_sections[current_host].setdefault(section_header, [])
        return PiggybackSectionParser(
            self.hostname,
            self.sections,
            self.piggyback_sections,
            current_host=current_host,
            current_section=section_header,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_piggyback_noop_parser(
        self,
        current_host: PiggybackMarker,
    ) -> "PiggybackNOOPParser":
        return PiggybackNOOPParser(
            self.hostname,
            self.sections,
            self.piggyback_sections,
            current_host=current_host,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_error(self, line: bytes) -> "ParserState":
        self._logger.warning(
            "%s: Ignoring invalid data %r",
            type(self).__name__,
            line,
            exc_info=True,
        )
        return self.to_noop_parser()

    @final
    def __call__(self, line: bytes) -> "ParserState":
        if not line.strip():
            return self

        try:
            if PiggybackMarker.is_header(line):
                return self.on_piggyback_header(line)
            if PiggybackMarker.is_footer(line):
                return self.on_piggyback_footer(line)
            if SectionMarker.is_header(line):
                return self.on_section_header(line)
            if SectionMarker.is_footer(line):
                return self.on_section_footer(line)
            return self.do_action(line)
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            return self.to_error(line)

        return self


class NOOPParser(ParserState):
    def do_action(self, line: bytes) -> "ParserState":
        return self

    def on_piggyback_header(self, line: bytes) -> "ParserState":
        piggyback_header = PiggybackMarker.from_headerline(
            line,
            self.translation,
            encoding_fallback=self.encoding_fallback,
        )
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self, line: bytes) -> "ParserState":
        return self

    def on_section_header(self, line: bytes) -> "ParserState":
        return self.to_host_section_parser(SectionMarker.from_headerline(line))

    def on_section_footer(self, line: bytes) -> "ParserState":
        # Optional
        return self.to_noop_parser()


class PiggybackParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        sections: MutableSection,
        piggyback_sections: MutableMapping[PiggybackMarker, MutableSection],
        *,
        current_host: PiggybackMarker,
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(
            hostname,
            sections,
            piggyback_sections,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.current_host: Final = current_host

    def do_action(self, line: bytes) -> "ParserState":
        # We are not in a section -> ignore line.
        return self

    def on_piggyback_header(self, line: bytes) -> "ParserState":
        piggyback_header = PiggybackMarker.from_headerline(
            line,
            self.translation,
            encoding_fallback=self.encoding_fallback,
        )
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self.to_noop_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self, line: bytes) -> "ParserState":
        return self.to_noop_parser()

    def on_section_header(self, line: bytes) -> "ParserState":
        return self.to_piggyback_section_parser(
            self.current_host,
            SectionMarker.from_headerline(line),
        )

    def on_section_footer(self, line: bytes) -> "ParserState":
        # Optional
        return self.to_piggyback_noop_parser(self.current_host)


class PiggybackSectionParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        sections: MutableSection,
        piggyback_sections: MutableMapping[PiggybackMarker, MutableSection],
        *,
        current_host: PiggybackMarker,
        current_section: SectionMarker,
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(
            hostname,
            sections,
            piggyback_sections,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.current_host: Final = current_host
        self.current_section: Final = current_section

    def do_action(self, line: bytes) -> "ParserState":
        self.piggyback_sections[self.current_host][self.current_section].append(AgentRawData(line))
        return self

    def on_piggyback_header(self, line: bytes) -> "ParserState":
        piggyback_header = PiggybackMarker.from_headerline(
            line,
            self.translation,
            encoding_fallback=self.encoding_fallback,
        )
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self, line: bytes) -> "ParserState":
        return self.to_noop_parser()

    def on_section_header(self, line: bytes) -> "ParserState":
        return self.to_piggyback_section_parser(
            self.current_host,
            SectionMarker.from_headerline(line),
        )

    def on_section_footer(self, line: bytes) -> "ParserState":
        # Optional
        return self.to_piggyback_noop_parser(self.current_host)


class PiggybackNOOPParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        sections: MutableSection,
        piggyback_sections: MutableMapping[PiggybackMarker, MutableSection],
        *,
        current_host: PiggybackMarker,
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(
            hostname,
            sections,
            piggyback_sections,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.current_host: Final = current_host

    def do_action(self, line: bytes) -> "PiggybackNOOPParser":
        return self

    def on_piggyback_header(self, line: bytes) -> "ParserState":
        piggyback_header = PiggybackMarker.from_headerline(
            line,
            self.translation,
            encoding_fallback=self.encoding_fallback,
        )
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self.to_noop_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self, line: bytes) -> "ParserState":
        return self.to_noop_parser()

    def on_section_header(self, line: bytes) -> "ParserState":
        return self.to_piggyback_section_parser(
            self.current_host,
            SectionMarker.from_headerline(line),
        )

    def on_section_footer(self, line: bytes) -> "ParserState":
        # Optional
        return self.to_piggyback_noop_parser(self.current_host)


class HostSectionParser(ParserState):
    def __init__(
        self,
        hostname: HostName,
        sections: MutableSection,
        piggyback_sections: MutableMapping[PiggybackMarker, MutableSection],
        *,
        current_section: SectionMarker,
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(
            hostname,
            sections,
            piggyback_sections,
            translation=translation,
            encoding_fallback=encoding_fallback,
            logger=logger,
        )
        self.current_section: Final = current_section

    def do_action(self, line: bytes) -> "ParserState":
        if not self.current_section.nostrip:
            line = line.strip()

        self.sections[self.current_section].append(AgentRawData(line))
        return self

    def on_piggyback_header(self, line: bytes) -> "ParserState":
        piggyback_header = PiggybackMarker.from_headerline(
            line,
            self.translation,
            encoding_fallback=self.encoding_fallback,
        )
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self, line: bytes) -> "ParserState":
        return self.to_noop_parser()

    def on_section_header(self, line: bytes) -> "ParserState":
        return self.to_host_section_parser(SectionMarker.from_headerline(line))

    def on_section_footer(self, line: bytes) -> "ParserState":
        # Optional
        return self.to_noop_parser()


class AgentParser(Parser[AgentRawData, AgentRawDataSection]):
    """A parser for agent data."""

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
        # Transform to seconds and give the piggybacked host a little bit more time
        self.cache_piggybacked_data_for: Final = int(1.5 * 60 * check_interval)
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
    ) -> HostSections[AgentRawDataSection]:
        if self.simulation:
            raw_data = agent_simulator.process(raw_data)

        now = int(time.time())

        raw_sections, piggyback_sections = self._parse_host_section(raw_data)
        section_info = {
            header.name: header
            for header in raw_sections
            if selection is NO_SELECTION or header.name in selection
        }

        def decode_sections(
            sections: ImmutableSection,
        ) -> MutableMapping[SectionName, List[AgentRawDataSection]]:
            out: MutableMapping[SectionName, List[AgentRawDataSection]] = {}
            for header, content in sections.items():
                out.setdefault(header.name, []).extend(header.parse_line(line) for line in content)
            return out

        def flatten_piggyback_section(
            sections: ImmutableSection,
            *,
            cached_at: int,
            cache_for: int,
            selection: SectionNameCollection,
        ) -> Iterator[bytes]:
            for header, content in sections.items():
                if not (selection is NO_SELECTION or header.name in selection):
                    continue

                if header.cached is not None or header.persist is not None:
                    yield str(header).encode(header.encoding)
                else:
                    # Add cache information.
                    yield str(
                        SectionMarker(
                            header.name,
                            (cached_at, cache_for),
                            header.encoding,
                            header.nostrip,
                            header.persist,
                            header.separator,
                        )
                    ).encode(header.encoding)
                yield from (bytes(line) for line in content)

        sections = {
            name: content
            for name, content in decode_sections(raw_sections).items()
            if selection is NO_SELECTION or name in selection
        }
        piggybacked_raw_data = {
            header.hostname: list(
                flatten_piggyback_section(
                    content,
                    cached_at=now,
                    cache_for=self.cache_piggybacked_data_for,
                    selection=selection,
                )
            )
            for header, content in piggyback_sections.items()
        }
        cache_info = {
            header.name: cache_info_tuple
            for header in section_info.values()
            if (cache_info_tuple := header.cache_info(now)) is not None
        }

        def lookup_persist(section_name: SectionName) -> Optional[Tuple[int, int]]:
            default = SectionMarker.default(section_name)
            if (until := section_info.get(section_name, default).persist) is not None:
                return now, until
            return None

        new_sections = self.section_store.update(
            sections,
            cache_info,
            lookup_persist,
            now=now,
            keep_outdated=self.keep_outdated,
        )
        return HostSections[AgentRawDataSection](
            new_sections,
            cache_info=cache_info,
            piggybacked_raw_data=piggybacked_raw_data,
        )

    def _parse_host_section(
        self,
        raw_data: AgentRawData,
    ) -> Tuple[ImmutableSection, Mapping[PiggybackMarker, ImmutableSection]]:
        """Split agent output in chunks, splits lines by whitespaces."""
        parser: ParserState = NOOPParser(
            self.hostname,
            {},
            {},
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )
        for line in raw_data.split(b"\n"):
            parser = parser(line.rstrip(b"\r"))

        return parser.sections, parser.piggyback_sections


class AgentSummarizer(Summarizer[AgentRawDataSection]):
    pass


class AgentSummarizerDefault(AgentSummarizer):
    def summarize_success(
        self,
        host_sections: HostSections[AgentRawDataSection],
        *,
        mode: Mode,
    ) -> Sequence[ActiveCheckResult]:
        # TODO: host_sections is not needed anymore. Doing something similar in the
        # IPMI DS will allow us to simplify things a lot.
        # Note: currently we *must not* return an empty sequence, because the datasource
        # will not be visible in the Check_MK service otherwise.
        return [ActiveCheckResult(0, "Success")]
