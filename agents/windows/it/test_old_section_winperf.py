#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import repeat
import os
import pytest
import re
from remote import actual_output, config, remotetest, wait_agent, write_config


class Globals(object):
    section = 'winperf'
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig_sections(request, config):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        config.set('global', 'sections', Globals.section)
    else:
        config.set('global', 'sections', '%s systemtime' % Globals.section)
    return config


@pytest.fixture(params=['System', '2'], ids=['counter:System', 'counter:2'])
def testconfig(request, testconfig_sections):
    testconfig_sections.set('global', 'crash_debug', 'yes')
    testconfig_sections.add_section(Globals.section)
    testconfig_sections.set(Globals.section, 'counters', '%s:test' % request.param)
    return testconfig_sections


@pytest.fixture
def expected_output():
    re_str = (r'\<\<\<winperf_(if|phydisk|processor|test)\>\>\>'
              r'|\d+\.\d{2} \d+ \d+'
              r'|\d+ instances\:( [^ ]+)+'
              r'|\-?\d+( \d+)+ [\w\(\)]+')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    return repeat(re_str)


def test_section_winperf(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
