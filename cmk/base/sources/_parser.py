#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.parser import (
    AgentParser,
    AgentRawDataSectionElem,
    Parser,
    PiggybackParser,
    SectionStore,
    SNMPParser,
)
from cmk.helper_interface import FetcherType
from cmk.utils.translations import parse_translation_options, TranslationOptions

__all__ = ["make_parser", "ParserConfig"]


@dataclasses.dataclass(frozen=True)
class ParserConfig:
    fallback_agent_output_encoding: str
    check_interval: Callable[[HostName], float]
    piggyback_translations: Callable[[HostName], Mapping[str, object]]
    # Nested callbacks. This is awfull and broken. CMK-25914
    # `value = piggyback_max_cache_age_callbacks(target_host_name)(source_host_name)`.
    piggyback_max_cache_age_callbacks: Callable[[HostAddress], Callable[[HostName], int]]

    def parsed_piggyback_translations(self, host_name: HostName) -> TranslationOptions:
        """Return the configured piggyback translations for a host"""
        return parse_translation_options(self.piggyback_translations(host_name))


def make_parser(
    config: ParserConfig,
    host_name: HostName,
    ip_address: HostAddress | None,
    fetcher_type: FetcherType,
    *,
    omd_root: Path,
    persisted_section_dir: Path,
    keep_outdated: bool,
    logger: logging.Logger,
) -> Parser:
    if fetcher_type is FetcherType.SNMP:
        return SNMPParser()

    section_store = SectionStore[Sequence[AgentRawDataSectionElem]](
        persisted_section_dir,
        logger=logger,
    )

    if fetcher_type is FetcherType.PIGGYBACK:
        return PiggybackParser(
            host_name,
            ip_address,
            section_store,
            omd_root,
            config.piggyback_max_cache_age_callbacks(host_name),
            keep_outdated=keep_outdated,
            encoding_fallback=config.fallback_agent_output_encoding,
            logger=logger,
        )

    return AgentParser(
        host_name,
        section_store,
        host_check_interval=config.check_interval(host_name),
        translation=config.parsed_piggyback_translations(host_name),
        keep_outdated=keep_outdated,
        encoding_fallback=config.fallback_agent_output_encoding,
        logger=logger,
    )
