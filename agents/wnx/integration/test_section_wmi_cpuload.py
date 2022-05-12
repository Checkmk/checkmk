#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re

import pytest  # type: ignore[import]

from . import it_utils
from .local import local_test


class Globals(object):
    section = "wmi_cpuload"
    alone = True


SYSTEM_PERF_HEADER = (
    r"Name,ProcessorQueueLength,Timestamp_PerfTime,Frequency_PerfTime,WMIStatus".replace(",", "\\|")
)
SYSTEM_PERF_BODY = r",\d+,\d+,\d+,\b(?:OK|Timeout)\b".replace(",", "\\|")

COMPUTER_SYSTEM_HEADER = r"Name,NumberOfLogicalProcessors,NumberOfProcessors,WMIStatus".replace(
    ",", "\\|"
)
COMPUTER_SYSTEM_BODY = r".*,\d+,\d+,\b(?:OK|Timeout)\b".replace(",", "\\|")


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(params=["alone", "with_systemtime"])
def testconfig(request, make_yaml_config):
    Globals.alone = request.param == "alone"
    if Globals.alone:
        make_yaml_config["global"]["sections"] = Globals.section
    else:
        make_yaml_config["global"]["sections"] = [Globals.section, "systemtime"]
    make_yaml_config["global"]["cpuload_method"] = "use_wmi"
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    expected = [
        re.escape(r"<<<%s:sep(124)>>>" % Globals.section),
        re.escape(r"[system_perf]"),
        SYSTEM_PERF_HEADER,
        SYSTEM_PERF_BODY,
        re.escape(r"[computer_system]"),
        COMPUTER_SYSTEM_HEADER,
        COMPUTER_SYSTEM_BODY,
    ]
    if not Globals.alone:
        expected += [re.escape(r"<<<systemtime>>>"), r"\d+"]
    return expected


def test_section_wmi_cpuload(request, testconfig, expected_output, actual_output, testfile):
    # special case, wmi may timeout
    required_lines = 7
    name = "cpu_load"

    if not it_utils.check_actual_input(name, required_lines, Globals.alone, actual_output):
        return

    local_test(expected_output, actual_output, testfile, request.node.name)
