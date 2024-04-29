#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from pathlib import Path

from cmk.utils.sectionname import SectionName

from cmk.snmplib import SNMPRawDataElem

from cmk.checkengine.fetcher import FetcherType, SourceInfo
from cmk.checkengine.parser import AgentRawDataSectionElem, Parser, SectionStore

from cmk.base.config import ConfigCache

__all__ = ["make_parser"]


def make_parser(
    config_cache: ConfigCache,
    source: SourceInfo,
    *,
    # Always from NO_SELECTION.
    checking_sections: frozenset[SectionName],
    persisted_section_dir: Path,
    keep_outdated: bool,
    logger: logging.Logger,
) -> Parser:
    hostname = source.hostname
    if source.fetcher_type is FetcherType.SNMP:
        return config_cache.make_snmp_parser(
            hostname,
            SectionStore[SNMPRawDataElem](
                persisted_section_dir,
                logger=logger,
            ),
            checking_sections=checking_sections,
            keep_outdated=keep_outdated,
            logger=logger,
        )

    return config_cache.make_agent_parser(
        hostname,
        SectionStore[Sequence[AgentRawDataSectionElem]](
            persisted_section_dir,
            logger=logger,
        ),
        keep_outdated=keep_outdated,
        logger=logger,
    )
