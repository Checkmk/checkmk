#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from itertools import chain, repeat
import os
import pytest  # type: ignore[import]
import re
from local import (actual_output, make_yaml_config, local_test, src_exec_dir, wait_agent,
                   write_config)


class Globals(object):
    section = 'services'
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
    re_str = (r'[\(\)$\w\.-]+ (unknown|continuing|pausing|paused|running|starting'
              r'|stopping|stopped)/(invalid1|invalid2|invalid3|invalid4|auto'
              r'|boot|demand|disabled|system|other) .+')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    return chain([re.escape(r'<<<%s>>>' % Globals.section)], repeat(re_str))


def test_section_services(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
