#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import SectionName

from cmk.checkengine import HostSections
from cmk.checkengine.type_defs import AgentRawDataSection


class TestHostSections:
    @pytest.fixture
    def host_sections(self) -> HostSections[AgentRawDataSection]:
        return self._get_some_section()

    def _get_some_section(self) -> HostSections[AgentRawDataSection]:
        return HostSections[AgentRawDataSection](
            {
                SectionName("section0"): [["first", "line"], ["second", "line"]],
                SectionName("section1"): [["third", "line"], ["forth", "line"]],
            },
            cache_info={
                SectionName("section0"): (1, 2),
                SectionName("section1"): (3, 4),
            },
            piggybacked_raw_data={
                HostName("host0"): [b"first line", b"second line"],
                HostName("host1"): [b"third line", b"forth line"],
            },
        )
