#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re

import pytest

from .local import local_test


class Globals(object):
    section = "uptime"
    alone = True


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
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    expected = [r"<<<%s>>>" % Globals.section, r"\d+"]
    if not Globals.alone:
        expected += [re.escape(r"<<<systemtime>>>"), r"\d+"]
    return expected


def test_section_uptime(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
