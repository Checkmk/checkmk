#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import pytest
import re
from remote import (actual_output, config, remotetest, remotedir, wait_agent, write_config)


class Globals(object):
    section = 'df'
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
    drive = r'[A-Z]:%s' % re.escape(os.sep)
    expected = [
        re.escape(r'<<<%s:sep(9)>>>' % Globals.section),
        r'%s\s+\w+\s+\d+\s+\d+\s+\d+\s+\d{1,3}%s\s+%s' % (drive, re.escape('%'), drive)
    ]
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


def test_section_df(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
