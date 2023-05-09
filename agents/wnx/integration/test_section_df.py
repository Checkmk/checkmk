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
    section = 'df'
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
    drive = r'[A-Z]:%s' % re.escape(os.sep)
    expected = [
        re.escape(r'<<<%s:sep(9)>>>' % Globals.section),
        r'(%s.*|\w+)\t\w*\t\d+\t\d+\t\d+\t\d{1,3}%s\t%s' % (drive, re.escape('%'), drive)
    ]
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


def test_section_df(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    result = actual_output
    actual_output_len = len(result)
    expected_output_len = len(expected_output)

    # if we have length mismatch we have to extend expected output
    # we will replicate expected strings depeding from length mismatching
    # the method is not elegant, but absolutelly correct
    for _ in range(expected_output_len, actual_output_len):
        expected_output.insert(1, expected_output[1])  # [h][1][f] ->[h][1][1][f] -> ...

    local_test(expected_output, actual_output, testfile, request.node.name)
