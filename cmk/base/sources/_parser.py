#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.fetcher import FetcherType
from cmk.checkengine.parser import (
    AgentParser,
    AgentRawDataSectionElem,
    Parser,
    SectionStore,
    SNMPParser,
)
from cmk.snmplib import SNMPRawDataElem
from cmk.utils.sectionname import SectionName
from cmk.utils.translations import parse_translation_options, TranslationOptions

__all__ = ["make_parser", "ParserConfig"]


@dataclasses.dataclass(frozen=True)
class ParserConfig:
    fallback_agent_output_encoding: str
    check_interval: Callable[[HostName], float]
    snmp_fetch_intervals: Callable[
        [HostName], Sequence[tuple[list[str], tuple[object, float | None]]]
    ]
    piggyback_translations: Callable[[HostName], Mapping[str, object]]

    def parsed_snmp_fetch_intervals(self, host_name: HostName) -> Mapping[SectionName, int | None]:
        """Return the configured SNMP fetch intervals for a host"""
        return {
            SectionName(section_name): None if seconds is None else round(seconds)
            for sections, (_option_id, seconds) in reversed(  # use first match
                self.snmp_fetch_intervals(host_name)
            )
            for section_name in sections
        }

    def parsed_piggyback_translations(self, host_name: HostName) -> TranslationOptions:
        """Return the configured piggyback translations for a host"""
        return parse_translation_options(self.piggyback_translations(host_name))


def make_parser(
    config: ParserConfig,
    host_name: HostName,
    fetcher_type: FetcherType,
    *,
    persisted_section_dir: Path,
    keep_outdated: bool,
    logger: logging.Logger,
) -> Parser:
    if fetcher_type is FetcherType.SNMP:
        return SNMPParser(
            host_name,
            SectionStore[SNMPRawDataElem](
                persisted_section_dir,
                logger=logger,
            ),
            persist_periods=config.parsed_snmp_fetch_intervals(host_name),
            host_check_interval=config.check_interval(host_name),
            keep_outdated=keep_outdated,
            logger=logger,
        )

    return AgentParser(
        host_name,
        SectionStore[Sequence[AgentRawDataSectionElem]](
            persisted_section_dir,
            logger=logger,
        ),
        host_check_interval=config.check_interval(host_name),
        translation=config.parsed_piggyback_translations(host_name),
        keep_outdated=keep_outdated,
        encoding_fallback=config.fallback_agent_output_encoding,
        logger=logger,
    )
