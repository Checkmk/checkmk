#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import pytest
from local import actual_output, make_ini_config, local_test, wait_agent, write_config


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(make_ini_config):
    section = 'systemtime'
    make_ini_config.set('global', 'sections', section)
    make_ini_config.set('global', 'crash_debug', 'yes')
    return make_ini_config


@pytest.fixture
def expected_output():
    return [r'<<<systemtime>>>', r'\d+']


def test_section_systemtime(testconfig, expected_output, actual_output, testfile):
    local_test(expected_output, actual_output, testfile)
