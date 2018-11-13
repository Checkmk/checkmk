#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import pytest
import re
from remote import actual_output, config, remotetest, wait_agent, write_config


class Globals(object):
    section = 'uptime'
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig(request, config):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        config.set('global', 'sections', Globals.section)
    else:
        config.set('global', 'sections', '%s systemtime' % Globals.section)
    config.set('global', 'crash_debug', 'yes')
    return config


@pytest.fixture
def expected_output():
    expected = [r'<<<%s>>>' % Globals.section, r'\d+']
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


def test_section_uptime(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
