#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import pytest
import re
from local import actual_output, make_ini_config, local_test, wait_agent, write_config


class Globals(object):
    section = 'uptime'
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig(request, make_ini_config):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        make_ini_config.set('global', 'sections', Globals.section)
    else:
        make_ini_config.set('global', 'sections', '%s systemtime' % Globals.section)
    make_ini_config.set('global', 'crash_debug', 'yes')
    return make_ini_config


@pytest.fixture
def expected_output():
    expected = [r'<<<%s>>>' % Globals.section, r'\d+']
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


def test_section_uptime(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
