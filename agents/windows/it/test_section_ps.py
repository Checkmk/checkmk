#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import pytest
import re
from remote import (actual_output, config, remotetest, remotedir, wait_agent,
                    write_config)

section = 'ps'


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['yes', 'no'], ids=['use_wmi=yes', 'use_wmi=no'])
def testconfig(request, config):
    config.set('global', 'sections', section)
    config.set('global', 'crash_debug', 'yes')
    config.add_section(section)
    config.set(section, 'use_wmi', request.param)
    return config


@pytest.fixture(params=['yes', 'no'], ids=['full_path=yes', 'full_path=no'])
def full_path_config(request, testconfig):
    testconfig.set(section, 'full_path', request.param)
    return testconfig


@pytest.fixture
def expected_output():
    return chain([re.escape(r'<<<ps:sep(9)>>>')],
                 repeat(r'\([^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+\)\s+'
                        r'(.+\.[Ee][Xx][Ee]|System( Idle Process)?)'))


def test_section_ps(request, full_path_config, expected_output, actual_output,
                    testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
