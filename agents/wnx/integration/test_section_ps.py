#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from itertools import chain, repeat

import pytest  # type: ignore[import]

from .local import local_test


class Globals:
    section = "ps"
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


@pytest.fixture(
    name="testconfig_use_wmi",
    params=["yes", "no"],
    ids=["use_wmi=yes", "use_wmi=no"],
)
def testconfig_use_wmi_engine(request, testconfig):
    testconfig["global"]["sections"] = Globals.section
    testconfig[Globals.section] = {"enabled": True, "use_wmi": request.param == "yes"}
    return testconfig


@pytest.fixture(
    name="full_path_config",
    params=["yes", "no"],
    ids=["full_path=yes", "full_path=no"],
)
def full_path_config_engine(request, testconfig_use_wmi):
    testconfig_use_wmi[Globals.section]["full_path"] = request.param
    return testconfig_use_wmi


@pytest.fixture(name="expected_output")
def expected_output_engine():
    # expected:
    # *.exe, *.dll, System, System( Idle Process), Registry,Memory Compression
    re_str = (
        r"\([^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+\)\s+"
        r"(.+(\.[Ee][Xx][Ee]|\.[Dd][Ll][Ll]|\.service)|System( Idle Process)?|Registry|Memory Compression|Secure System|vmmem|com.docker.service)"
    )
    if not Globals.alone:
        re_str += r"|" + re.escape(r"<<<systemtime>>>") + r"|\d+"

    # ***************************************
    # method is not the best one, still works
    # we have output:
    # string_normal|string_for_systemtime
    # ......
    # string_normal|string_for_systemtime
    # instead of:
    # string_normal
    # ......
    # string_normal
    # string_for_systemtime
    # ***************************************
    return chain([re.escape(r"<<<ps:sep(9)>>>")], repeat(re_str))


def test_section_ps(request, full_path_config, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
