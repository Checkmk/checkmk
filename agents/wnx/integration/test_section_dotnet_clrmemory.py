#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from itertools import chain, repeat

import pytest  # type: ignore

from . import it_utils
from .local import local_test


class Globals:
    section = "dotnet_clrmemory"
    alone = True


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(name="testconfig", params=["alone", "with_systemtime"])
def testconfig_engine(request, make_yaml_config):
    Globals.alone = request.param == "alone"
    if Globals.alone:
        make_yaml_config["global"]["sections"] = Globals.section
    else:
        make_yaml_config["global"]["sections"] = [Globals.section, "systemtime"]
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    base = [
        re.escape(r"<<<%s:sep(124)>>>" % Globals.section),
        (
            r"AllocatedBytesPersec,Caption,Description,FinalizationSurvivors,"
            r"Frequency_Object,Frequency_PerfTime,Frequency_Sys100NS,Gen0heapsize,"
            r"Gen0PromotedBytesPerSec,Gen1heapsize,Gen1PromotedBytesPerSec,"
            r"Gen2heapsize,LargeObjectHeapsize,Name,NumberBytesinallHeaps,"
            r"NumberGCHandles,NumberGen0Collections,NumberGen1Collections,"
            r"NumberGen2Collections,NumberInducedGC,NumberofPinnedObjects,"
            r"NumberofSinkBlocksinuse,NumberTotalcommittedBytes,"
            r"NumberTotalreservedBytes,PercentTimeinGC,PercentTimeinGC_Base,"
            r"ProcessID,PromotedFinalizationMemoryfromGen0,PromotedMemoryfromGen0,"
            r"PromotedMemoryfromGen1,Timestamp_Object,Timestamp_PerfTime,"
            r"Timestamp_Sys100NS"
        ).replace(",", "\\|"),
    ]
    re_str = (
        r"\d+,,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,"
        r"[\w\#\.]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,"
        r"\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+"
    ).replace(",", "\\|")
    if not Globals.alone:
        re_str += r"|" + re.escape(r"<<<systemtime>>>") + r"|\d+"
    return chain(base, repeat(re_str))


def test_section_dotnet_clrmemory(request, testconfig, expected_output, actual_output, testfile):
    # special case wmi may timeout
    required_lines = 5
    name = "dotnet"

    if not it_utils.check_actual_input(name, required_lines, Globals.alone, actual_output):
        return

    local_test(expected_output, actual_output, testfile, request.node.name)
