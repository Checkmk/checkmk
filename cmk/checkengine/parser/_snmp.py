#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.snmplib import SNMPRawData

from ._markers import SectionMarker
from ._parser import HostSections, Parser, SNMPParsedData

__all__ = ["SNMPParser"]


class SNMPParser(Parser[SNMPRawData, SNMPParsedData]):
    """A parser for SNMP data"""

    def parse(
        self,
        raw_data: SNMPRawData,
        *,
        # The selection argument is ignored: Selection is done
        # in the fetcher for SNMP.
        selection: object,
    ) -> HostSections[SNMPParsedData]:
        marked_sections = {SectionMarker.from_header(n): content for n, content in raw_data.items()}
        return HostSections[SNMPParsedData](
            sections={marker.name: content for marker, content in marked_sections.items()},
            cache_info={marker.name: marker.cached for marker in marked_sections if marker.cached},
            piggybacked_raw_data={},
        )
