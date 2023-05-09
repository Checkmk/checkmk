#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest  # type: ignore
import re
from local import actual_output, make_yaml_config, local_test, wait_agent, write_config


class Globals(object):
    section = 'mem'
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig(request, make_yaml_config):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        make_yaml_config['global']['sections'] = Globals.section
    else:
        make_yaml_config['global']['sections'] = [Globals.section, "systemtime"]
    return make_yaml_config


@pytest.fixture
def expected_output():
    expected = [
        r'<<<mem>>>',  #
        r'MemTotal:\s+\d+\skB',  #
        r'MemFree:\s+\d+\skB',  #
        r'SwapTotal:\s+\d+\skB',  #
        r'SwapFree:\s+\d+\skB',  #
        r'PageTotal:\s+\d+\skB',  #
        r'PageFree:\s+\d+\skB',  #
        r'VirtualTotal:\s+\d+\skB',  #
        r'VirtualFree:\s+\d+\skB'  #
    ]
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


def test_section_mem(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
