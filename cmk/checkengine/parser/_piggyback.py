#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Final

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.helper_interface import AgentRawData
from cmk.piggyback.backend import get_messages_for, PiggybackMessage

from ._agent import (
    ImmutableSection,
    make_cache_info,
    make_decoded_sections,
    make_persisting_info,
    make_section_info,
    NOOPParser,
    ParserState,
)
from ._parser import (
    AgentRawDataSection,
    AgentRawDataSectionElem,
    HostSections,
    NO_SELECTION,
    Parser,
    SectionNameCollection,
)
from ._sectionstore import SectionStore


class PiggybackParser(Parser[AgentRawData, AgentRawDataSection]):
    """A parser for piggyback data."""

    def __init__(
        self,
        hostname: HostName,
        ip_address: HostAddress | None,
        section_store: SectionStore[Sequence[AgentRawDataSectionElem]],
        omd_root: Path,
        piggyback_max_cache_age: Callable[[HostAddress], int],
        *,
        keep_outdated: bool,
        encoding_fallback: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.address: Final = ip_address
        self.section_store: Final = section_store
        self.omd_root: Final = omd_root
        self.piggyback_max_cache_age: Final = piggyback_max_cache_age
        self.keep_outdated: Final = keep_outdated
        self.encoding_fallback: Final = encoding_fallback
        self._logger = logger

    def parse(
        self,
        raw_data: AgentRawData,
        *,
        selection: SectionNameCollection,
    ) -> HostSections[AgentRawDataSection]:
        now = int(time.time())

        # we expect raw_data to be empty here, but just extend it to avoid surprises.
        raw_data = AgentRawData(raw_data + self._make_piggyback_data())

        raw_sections = self._parse_host_section(raw_data, selection)
        section_info = make_section_info(raw_sections)
        sections = make_decoded_sections(raw_sections)
        cache_info = make_cache_info(section_info, now)

        new_sections = self.section_store.update(
            sections,
            cache_info,
            make_persisting_info(section_info),
            lambda valid_until, now: valid_until < now,
            now=now,
            keep_outdated=self.keep_outdated,
        )
        return HostSections[AgentRawDataSection](
            new_sections,
            cache_info=cache_info,
        )

    def _parse_host_section(
        self,
        raw_data: AgentRawData,
        selection: SectionNameCollection,
    ) -> ImmutableSection:
        """Split agent output in chunks, splits lines by whitespaces."""
        parser: ParserState = NOOPParser(
            self.hostname,
            [],
            {},
            translation={},  # there are no "nested" piggyback sections
            encoding_fallback=self.encoding_fallback,
            logger=self._logger,
        )
        for line in raw_data.split(b"\n"):
            parser = parser(line.rstrip(b"\r"))

        return (
            parser.sections
            if selection is NO_SELECTION
            else [s for s in parser.sections if s.header.name in selection]
        )

    def _make_piggyback_data(self) -> AgentRawData:
        self._logger.debug("Get piggybacked data")
        if not (
            sources := [
                line
                for origin in (self.hostname, self.address)
                if origin
                for line in self._raw_data(origin, self.omd_root)
            ]
        ):
            return AgentRawData(b"")
        return AgentRawData(
            self._get_source_summary_section(sources)
            + self._get_source_labels_section(sources)
            + self._get_main_section(sources)
        )

    def _get_main_section(self, sources: Iterable[PiggybackMessage]) -> bytearray:
        raw_data = bytearray()
        for src in sources:
            if (time.time() - src.meta.last_update) <= self.piggyback_max_cache_age(
                src.meta.source
            ):
                # !! Important for Check_MK and Check_MK Discovery service !!
                #   - sources contains ALL file infos and is not filtered
                #     in cmk/base/piggyback.py as in previous versions
                #   - Check_MK gets the processed file info reasons and displays them in
                #     it's service details
                #   - Check_MK Discovery: Only shows vanished/new/... if raw data is not
                #     added; ie. if file_info is not successfully processed
                raw_data += src.raw_data
        return raw_data

    def _get_source_summary_section(self, sources: Iterable[PiggybackMessage]) -> bytes:
        """Add some meta information about the piggyback sources to the agent output.

        The fetcher messages currently lack the capability to add additional meta information
        to the sources (other than one single exception).
        Since we're adding payload anyway, we add this section as well, to be consumed by the summarizer.
        """
        return f"<<<piggyback_source_summary:sep(0)>>>\n{'\n'.join(s.meta.serialize() for s in sources)}\n".encode()

    def _get_source_labels_section(self, sources: Iterable[PiggybackMessage]) -> bytes:
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        labels = {"cmk/piggyback_source_%s" % src.meta.source: "yes" for src in sources}
        return ("<<<labels:sep(0)>>>\n%s\n" % json.dumps(labels)).encode("utf-8")

    @staticmethod
    def _raw_data(hostname: HostAddress, omd_root: Path) -> Sequence[PiggybackMessage]:
        return get_messages_for(hostname, omd_root)
