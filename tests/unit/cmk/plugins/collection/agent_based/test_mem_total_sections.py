#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.plugins.collection.agent_based.mem_total_sections import parse_mem_total_solaris
from cmk.plugins.lib.memory import SectionMemTotal


def test_simple():
    assert parse_mem_total_solaris([["Memory size: 123904 Megabytes"]]) == SectionMemTotal(
        129922760704
    )


def test_problem():
    with pytest.raises(ValueError, match=r"can not parse \[\['something'\]\]"):
        parse_mem_total_solaris([["something"]])
