#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import pytest
import re
from local import (actual_output, make_ini_config, local_test, src_exec_dir, wait_agent,
                   write_config)


class Globals(object):
    section = 'ps'
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['yes', 'no'], ids=['use_wmi=yes', 'use_wmi=no'])
def testconfig(request, make_ini_config):
    make_ini_config.set('global', 'sections', Globals.section)
    make_ini_config.set('global', 'crash_debug', 'yes')
    make_ini_config.add_section(Globals.section)
    make_ini_config.set(Globals.section, 'use_wmi', request.param)
    return make_ini_config


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig_sections(request, testconfig):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        testconfig.set('global', 'sections', Globals.section)
    else:
        testconfig.set('global', 'sections', '%s systemtime' % Globals.section)
    return testconfig


@pytest.fixture(params=['yes', 'no'], ids=['full_path=yes', 'full_path=no'])
def full_path_config(request, testconfig_sections):
    testconfig_sections.set(Globals.section, 'full_path', request.param)
    return testconfig_sections


@pytest.fixture
def expected_output():
    re_str = (r'\([^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+\)\s+'
              r'(.+\.[Ee][Xx][Ee]|System( Idle Process)?)')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    return chain([re.escape(r'<<<ps:sep(9)>>>')], repeat(re_str))


def test_section_ps(request, full_path_config, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
