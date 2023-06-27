#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import SectionName

from cmk.checkengine.host_sections import HostSections
from cmk.checkengine.type_defs import AgentRawDataSection


class TestHostSections:
    @pytest.fixture
    def host_sections(self) -> HostSections:
        return self._get_some_section()

    @pytest.fixture
    def identical_host_sections(self) -> HostSections:
        return self._get_some_section()

    def _get_some_section(self) -> HostSections:
        return HostSections[Sequence[AgentRawDataSection]](
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

    def test_add_self_extends_sections(
        self, host_sections: HostSections, identical_host_sections: HostSections
    ) -> None:
        # host_sections will be modified inline
        result = host_sections + identical_host_sections
        assert id(result) == id(host_sections)

        assert result.sections.keys() == host_sections.sections.keys()
        assert result.cache_info.keys() == host_sections.cache_info.keys()
        assert result.piggybacked_raw_data.keys() == host_sections.piggybacked_raw_data.keys()

        for section in host_sections.sections:
            assert result.sections[section] == 2 * list(identical_host_sections.sections[section])
        assert result.cache_info == host_sections.cache_info
        for host_name in host_sections.piggybacked_raw_data:
            assert result.piggybacked_raw_data[host_name] == 2 * list(
                identical_host_sections.piggybacked_raw_data[host_name]
            )

    def test_add_other_adds_sections(self, host_sections: HostSections) -> None:
        other = HostSections[Sequence[AgentRawDataSection]](
            {
                SectionName("section2"): [["first", "line"], ["second", "line"]],
                SectionName("section3"): [["third", "line"], ["forth", "line"]],
                SectionName("section4"): [["fifth", "line"], ["sixth", "line"]],
            },
            cache_info={
                SectionName("section2"): (1, 2),
                SectionName("section3"): (3, 4),
            },
            piggybacked_raw_data={
                HostName("host2"): [b"first line", b"second line"],
                HostName("host3"): [b"third line", b"forth line"],
            },
        )

        num_previous_sections = len(host_sections.sections)
        num_previous_piggyback = len(host_sections.piggybacked_raw_data)
        num_previous_cache_info = len(host_sections.cache_info)

        # host_sections will be modified inline
        result = host_sections + other
        assert id(result) == id(host_sections)
        assert len(result.sections) == num_previous_sections + len(other.sections)
        assert len(result.cache_info) == num_previous_cache_info + len(other.cache_info)
        assert len(result.piggybacked_raw_data) == num_previous_piggyback + len(
            other.piggybacked_raw_data
        )
