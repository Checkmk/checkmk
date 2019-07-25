#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import platform
import pytest
import re
import shutil
import time
import it_utils
from local import (actual_output, assert_subprocess, make_yaml_config, local_test, write_config,
                   user_dir)


class Globals(object):
    it_utils.stop_ohm()
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=[('openhardwaremonitor', True), ('openhardwaremonitor', False)],
                ids=['sections=openhardwaremonitor', 'sections=openhardwaremonitor_systemtime'])
def testconfig(request, make_yaml_config):
    Globals.alone = request.param[1]
    if Globals.alone:
        make_yaml_config['global']['sections'] = request.param[0]
    else:
        make_yaml_config['global']['sections'] = [request.param[0], "systemtime"]
    return make_yaml_config


@pytest.fixture
def wait_agent():
    def inner():
        # Wait a little so that OpenHardwareMonitorCLI.exe starts properly.
        time.sleep(10)
        return True

    return inner


@pytest.fixture
def expected_output():
    re_str = (r'^\d+,[^,]+,(\/\w+)+,(Power|Clock|Load|Data|Temperature),'
              r'\d+\.\d{6},\b(?:OK|Timeout)\b')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    re_str += r'$'
    return chain(
        [re.escape(r'<<<openhardwaremonitor:sep(44)>>>'), r'Index,Name,Parent,SensorType,Value'],
        repeat(re_str))


@pytest.fixture(autouse=True)
def manage_ohm_binaries():
    if platform.system() == 'Windows':
        binaries = ['OpenHardwareMonitorCLI.exe', 'OpenHardwareMonitorLib.dll']

        source_dir = os.path.join(os.path.abspath(__file__), "..\\..\\test_files\\ohm\\cli")
        target_dir = os.path.join(user_dir, 'bin')

        it_utils.make_dir(target_dir)

        for f in binaries:
            shutil.copy(os.path.join(source_dir, f), target_dir)
    yield
    if platform.system() == 'Windows':
        it_utils.stop_ohm()
        binaries.append("OpenHardwareMonitorLib.sys")
        it_utils.remove_files(target_dir, binaries)


def test_section_openhardwaremonitor(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
