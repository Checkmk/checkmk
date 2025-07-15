#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from cmk.ccc.hostaddress import HostName

from cmk.snmplib import SNMPRawDataElem

from cmk.checkengine.fetcher import FetcherType
from cmk.checkengine.parser import AgentRawDataSectionElem, Parser, SectionStore

__all__ = ["make_parser", "ParserFactory"]


class ParserFactory(Protocol):
    def make_snmp_parser(
        self,
        hostname: HostName,
        section_store: SectionStore[SNMPRawDataElem],
        *,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> Parser: ...

    def make_agent_parser(
        self,
        hostname: HostName,
        section_store: SectionStore[Sequence[AgentRawDataSectionElem]],
        *,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> Parser: ...


def make_parser(
    factory: ParserFactory,
    hostname: HostName,
    fetcher_type: FetcherType,
    *,
    persisted_section_dir: Path,
    keep_outdated: bool,
    logger: logging.Logger,
) -> Parser:
    if fetcher_type is FetcherType.SNMP:
        return factory.make_snmp_parser(
            hostname,
            SectionStore[SNMPRawDataElem](
                persisted_section_dir,
                logger=logger,
            ),
            keep_outdated=keep_outdated,
            logger=logger,
        )

    return factory.make_agent_parser(
        hostname,
        SectionStore[Sequence[AgentRawDataSectionElem]](
            persisted_section_dir,
            logger=logger,
        ),
        keep_outdated=keep_outdated,
        logger=logger,
    )
