#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from itertools import repeat

import pytest

from .local import local_test


class Globals:
    section = "winperf"
    alone = True


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(name="testconfig_sections", params=["alone", "with_systemtime"])
def fixture_testconfig_sections(request, make_yaml_config):
    Globals.alone = request.param == "alone"
    if Globals.alone:
        make_yaml_config["global"]["sections"] = Globals.section
    else:
        make_yaml_config["global"]["sections"] = [Globals.section, "systemtime"]
    return make_yaml_config


@pytest.fixture(name="testconfig", params=["System", "2"], ids=["counter:System", "counter:2"])
def fixture_testconfig(request, testconfig_sections):
    testconfig_sections[Globals.section] = {"counters": ["%s:test" % request.param]}
    return testconfig_sections


@pytest.fixture(name="expected_output")
def expected_output_engine():
    re_str = (
        r"\<\<\<winperf_(if|phydisk|processor|test)\>\>\>"
        r"|\d+\.\d{2} \d+ \d+"
        r"|\d+ instances\:( [^ ]+)+"
        r"|\-?\d+( \d+)+ [\w\(\)]+"
        r"|\d\d\d[2|6]( .+)+ text"
    )
    if not Globals.alone:
        re_str += r"|" + re.escape(r"<<<systemtime>>>") + r"|\d+"
    return repeat(re_str)


def test_section_winperf(  # type: ignore[no-untyped-def]
    request, testconfig, expected_output, actual_output, testfile
) -> None:
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
