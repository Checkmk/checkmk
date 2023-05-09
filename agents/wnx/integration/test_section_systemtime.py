#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest  # type: ignore[import]
from local import actual_output, make_yaml_config, local_test, wait_agent, write_config


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(make_yaml_config):
    section = 'systemtime'
    make_yaml_config['global']['sections'] = "systemtime"
    return make_yaml_config


@pytest.fixture
def expected_output():
    return [r'<<<systemtime>>>', r'\d+']


def test_section_systemtime(testconfig, expected_output, actual_output, testfile):
    local_test(expected_output, actual_output, testfile)
