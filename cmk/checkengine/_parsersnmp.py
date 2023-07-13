#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Final

from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import HostSection, SectionName

from cmk.snmplib.type_defs import SNMPRawData

from cmk.fetchers.cache import SectionStore

from ._parser import Parser
from .host_sections import HostSections
from .type_defs import SectionNameCollection

__all__ = ["SNMPParser"]


class SNMPParser(Parser[HostSection[Sequence[SNMPRawData]], HostSections[Sequence[SNMPRawData]]]):
    """A parser for SNMP data.

    Note:
        It is forbidden to add base dependencies to this class.

    """

    def __init__(
        self,
        hostname: HostName,
        section_store: SectionStore[Sequence[SNMPRawData]],
        *,
        check_intervals: Mapping[SectionName, int | None],
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.check_intervals: Final = check_intervals
        self.section_store: Final = section_store
        self.keep_outdated: Final = keep_outdated
        self._logger = logger

    def parse(
        self,
        raw_data: HostSection[Sequence[SNMPRawData]],
        *,
        # The selection argument is ignored: Selection is done
        # in the fetcher for SNMP.
        selection: SectionNameCollection,
    ) -> HostSections[Sequence[SNMPRawData]]:
        sections = dict(raw_data)
        now = int(time.time())

        def lookup_persist(section_name: SectionName) -> tuple[int, int] | None:
            if (interval := self.check_intervals.get(section_name)) is not None:
                return now, now + interval
            return None

        cache_info: MutableMapping[SectionName, tuple[int, int]] = {}
        new_sections = self.section_store.update(
            sections,
            cache_info,
            lookup_persist,
            now=now,
            keep_outdated=self.keep_outdated,
        )
        return HostSections[Sequence[SNMPRawData]](new_sections, cache_info=cache_info)
