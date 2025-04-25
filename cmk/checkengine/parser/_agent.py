#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import logging
import time
from collections.abc import Iterator, Mapping, MutableMapping, Sequence
from typing import Final, final, NamedTuple

import cmk.ccc.debug
from cmk.ccc.hostaddress import HostName

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.sectionname import MutableSectionMap, SectionName
from cmk.utils.translations import TranslationOptions

from ._markers import PiggybackMarker, SectionMarker
from ._parser import (
    AgentRawDataSection,
    AgentRawDataSectionElem,
    HostSections,
    NO_SELECTION,
    Parser,
    SectionNameCollection,
)
from ._sectionstore import SectionStore


class SectionWithHeader(NamedTuple):
    header: SectionMarker
    section: list[AgentRawData]


MutableSection = list[SectionWithHeader]
ImmutableSection = Sequence[SectionWithHeader]


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

        Host --> IgnoredPiggybackedHost : ""<<<~<.>>>>""
        IgnoredPiggybackedHost --> Host : ""<<<~<>>>>""

        PiggybackedHost --> IgnoredPiggybackedHost : ""<<<~<.>>>>""
        IgnoredPiggybackedHost --> PiggybackedHost : ""<<<~<HOSTNAME>>>>""

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
    def do_action(self, line: bytes) -> ParserState:
        raise NotImplementedError()

    @abc.abstractmethod
    def on_section_header(self, section_header: SectionMarker) -> ParserState:
        raise NotImplementedError()

    @abc.abstractmethod
    def on_section_footer(self) -> ParserState:
        raise NotImplementedError()

    @abc.abstractmethod
    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        raise NotImplementedError()

    @abc.abstractmethod
    def on_piggyback_footer(self) -> ParserState:
        raise NotImplementedError()

    def to_noop_parser(self) -> NOOPParser:
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
    ) -> HostSectionParser:
        self._logger.debug(
            "%s / Transition %s -> %s",
            section_header,
            type(self).__name__,
            HostSectionParser.__name__,
        )
        if not self.sections or self.sections[-1].header != section_header:
            self.sections.append(SectionWithHeader(section_header, []))
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
    ) -> PiggybackParser:
        self._logger.debug(
            "%s / Transition %s -> %s",
            header,
            type(self).__name__,
            PiggybackParser.__name__,
        )
        self.piggyback_sections.setdefault(header, [])
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
    ) -> PiggybackSectionParser:
        self._logger.debug(
            "%r %r / Transition %s -> %s",
            current_host,
            section_header,
            type(self).__name__,
            PiggybackSectionParser.__name__,
        )
        if (
            not self.piggyback_sections[current_host]
            or self.piggyback_sections[current_host][-1].header != section_header
        ):
            self.piggyback_sections[current_host].append(SectionWithHeader(section_header, []))
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
    ) -> PiggybackNOOPParser:
        return PiggybackNOOPParser(
            self.hostname,
            self.sections,
            self.piggyback_sections,
            current_host=current_host,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_piggyback_ignore_parser(self) -> PiggybackIgnoreParser:
        return PiggybackIgnoreParser(
            self.hostname,
            self.sections,
            self.piggyback_sections,
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )

    def to_error(self, line: bytes) -> ParserState:
        self._logger.warning(
            "%s: Ignoring invalid data %r",
            type(self).__name__,
            line,
            exc_info=True,
        )
        return self.to_noop_parser()

    @final
    def __call__(self, line: bytes) -> ParserState:
        if not line or line.isspace():
            return self

        try:
            if line.startswith(b"<<<") and line.endswith(b">>>"):
                # The condition below implies the condition above. A nicer way would be lifting the
                # "if" below before the "if" above, but for performance reasons we nest it here.
                if line.startswith(b"<<<<") and line.endswith(b">>>>"):
                    return (
                        self.on_piggyback_header(
                            PiggybackMarker.from_header(
                                header, self.translation, encoding_fallback=self.encoding_fallback
                            )
                        )
                        if (header := line[4:-4])
                        else self.on_piggyback_footer()
                    )
                # There is no section footer in the protocol but some non-compliant plugins still
                # add one and we accept it.
                return (
                    self.on_section_header(SectionMarker.from_header(header))
                    if (header := line[3:-3]) and not header.startswith(b":")
                    else self.on_section_footer()
                )
            return self.do_action(line)
        except Exception:
            if cmk.ccc.debug.enabled():
                raise
            return self.to_error(line)


class NOOPParser(ParserState):
    def do_action(self, line: bytes) -> ParserState:
        return self

    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self
        if piggyback_header.should_be_ignored():
            return self.to_piggyback_ignore_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self) -> ParserState:
        return self

    def on_section_header(self, section_header: SectionMarker) -> ParserState:
        return self.to_host_section_parser(section_header)

    def on_section_footer(self) -> ParserState:
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

    def do_action(self, line: bytes) -> ParserState:
        # We are not in a section -> ignore line.
        return self

    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self.to_noop_parser()
        if piggyback_header.should_be_ignored():
            return self.to_piggyback_ignore_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self) -> ParserState:
        return self.to_noop_parser()

    def on_section_header(self, section_header: SectionMarker) -> ParserState:
        return self.to_piggyback_section_parser(self.current_host, section_header)

    def on_section_footer(self) -> ParserState:
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

    def do_action(self, line: bytes) -> ParserState:
        self.piggyback_sections[self.current_host][-1].section.append(AgentRawData(line))
        return self

    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        if piggyback_header.should_be_ignored():
            return self.to_piggyback_ignore_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self) -> ParserState:
        return self.to_noop_parser()

    def on_section_header(self, section_header: SectionMarker) -> ParserState:
        return self.to_piggyback_section_parser(self.current_host, section_header)

    def on_section_footer(self) -> ParserState:
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

    def do_action(self, line: bytes) -> PiggybackNOOPParser:
        return self

    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self.to_noop_parser()
        if piggyback_header.should_be_ignored():
            return self.to_piggyback_ignore_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self) -> ParserState:
        return self.to_noop_parser()

    def on_section_header(self, section_header: SectionMarker) -> ParserState:
        return self.to_piggyback_section_parser(self.current_host, section_header)

    def on_section_footer(self) -> ParserState:
        # Optional
        return self.to_piggyback_noop_parser(self.current_host)


class PiggybackIgnoreParser(ParserState):
    def do_action(self, line: bytes) -> PiggybackIgnoreParser:
        return self

    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self.to_noop_parser()
        if piggyback_header.should_be_ignored():
            return self.to_piggyback_ignore_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self) -> ParserState:
        return self.to_noop_parser()

    def on_section_header(self, section_header: SectionMarker) -> PiggybackIgnoreParser:
        return self

    def on_section_footer(self) -> PiggybackIgnoreParser:
        return self


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

    def do_action(self, line: bytes) -> ParserState:
        self.sections[-1].section.append(
            AgentRawData(line if self.current_section.nostrip else line.strip())
        )
        return self

    def on_piggyback_header(self, piggyback_header: PiggybackMarker) -> ParserState:
        if piggyback_header.hostname == self.hostname:
            # Unpiggybacked "normal" host
            return self
        if piggyback_header.should_be_ignored():
            return self.to_piggyback_ignore_parser()
        return self.to_piggyback_parser(piggyback_header)

    def on_piggyback_footer(self) -> ParserState:
        return self.to_noop_parser()

    def on_section_header(self, section_header: SectionMarker) -> ParserState:
        return self.to_host_section_parser(section_header)

    def on_section_footer(self) -> ParserState:
        # Optional
        return self.to_noop_parser()


class AgentParser(Parser[AgentRawData, AgentRawDataSection]):
    """A parser for agent data."""

    def __init__(
        self,
        hostname: HostName,
        section_store: SectionStore[Sequence[AgentRawDataSectionElem]],
        *,
        host_check_interval: float,
        keep_outdated: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        # give the piggybacked host a little bit more time
        self.cache_piggybacked_data_for: Final = int(1.5 * host_check_interval)
        self.section_store: Final = section_store
        self.keep_outdated: Final = keep_outdated
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self._logger = logger

    def parse(
        self,
        raw_data: AgentRawData,
        *,
        selection: SectionNameCollection,
    ) -> HostSections[AgentRawDataSection]:
        now = int(time.time())

        raw_sections, piggyback_sections = self._parse_host_section(raw_data)
        section_info = {
            header.name: header
            for header, _ in raw_sections
            if selection is NO_SELECTION or header.name in selection
        }

        def decode_sections(
            sections: ImmutableSection,
        ) -> MutableSectionMap[list[AgentRawDataSectionElem]]:
            out: MutableSectionMap[list[AgentRawDataSectionElem]] = {}
            for header, content in sections:
                out.setdefault(header.name, []).extend(header.parse_line(line) for line in content)
            return out

        def flatten_piggyback_section(
            sections: ImmutableSection,
            *,
            cached_at: int,
            cache_for: int,
            selection: SectionNameCollection,
        ) -> Iterator[bytes]:
            for header, content in sections:
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
            if header.hostname is not None
        }
        cache_info = {
            header.name: cache_info_tuple
            for header in section_info.values()
            if (cache_info_tuple := header.cache_info(now)) is not None
        }

        def lookup_persist(section_name: SectionName) -> tuple[int, int] | None:
            default = SectionMarker.default(section_name)
            if (until := section_info.get(section_name, default).persist) is not None:
                return now, until
            return None

        new_sections = self.section_store.update(
            sections,
            cache_info,
            lookup_persist,
            lambda valid_until, now: valid_until < now,
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
    ) -> tuple[ImmutableSection, Mapping[PiggybackMarker, ImmutableSection]]:
        """Split agent output in chunks, splits lines by whitespaces."""
        parser: ParserState = NOOPParser(
            self.hostname,
            [],
            {},
            translation=self.translation,
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )
        for line in raw_data.split(b"\n"):
            parser = parser(line.rstrip(b"\r"))

        return parser.sections, parser.piggyback_sections
