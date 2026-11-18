#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugins import SectionName
from cmk.checkengine.snmplib import SNMPSectionName
from cmk.plugins.checkmk.cli.handlers._snmp_fetcher import snmp_section_selection


def test_without_a_section_selection_no_snmp_section_is_selected() -> None:
    assert isinstance(
        snmp_section_selection(NO_SELECTION, {SectionName("ifs")}), NoSelectedSNMPSections
    )


def test_a_section_selection_keeps_only_the_snmp_sections() -> None:
    assert snmp_section_selection(
        frozenset({SectionName("ifs"), SectionName("df")}), {SectionName("ifs")}
    ) == frozenset({SNMPSectionName("ifs")})
