#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import yaml
import os
import pytest
import re
from local import (actual_output, make_yaml_config, local_test, wait_agent, write_config)


class Globals(object):
    section = 'ps'
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


@pytest.fixture(params=['yes', 'no'], ids=['use_wmi=yes', 'use_wmi=no'])
def testconfig_use_wmi(request, testconfig):
    testconfig['global']['sections'] = Globals.section
    testconfig[Globals.section] = {
        'enabled': True,
        'use_wmi': True if request.param == 'yes' else False
    }
    return testconfig


@pytest.fixture(params=['yes', 'no'], ids=['full_path=yes', 'full_path=no'])
def full_path_config(request, testconfig_use_wmi):
    testconfig_use_wmi[Globals.section]['full_path'] = request.param
    return testconfig_use_wmi


@pytest.fixture
def expected_output():
    # expected:
    # *.exe, *.dll, System, System( Idle Process), Registry,Memory Compression
    re_str = (
        r'\([^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+\)\s+'
        r'(.+(\.[Ee][Xx][Ee]|\.[Dd][Ll][Ll])|System( Idle Process)?|Registry|Memory Compression)')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'

    # ***************************************
    # method is not the best one, still works
    # we have output:
    # string_normal|string_for_systemtime
    # ......
    # string_normal|string_for_systemtime
    # instead of:
    # string_normal
    # ......
    # string_normal
    # string_for_systemtime
    # ***************************************
    return chain([re.escape(r'<<<ps:sep(9)>>>')], repeat(re_str))


def test_section_ps(request, full_path_config, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
