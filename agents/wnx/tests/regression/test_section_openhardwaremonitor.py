#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import platform
import re
import shutil
import time
from itertools import chain, repeat

import pytest

from . import it_utils
from .local import local_test, user_dir


class Globals:
    it_utils.stop_ohm()
    alone = True


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(
    name="testconfig",
    params=[("openhardwaremonitor", True), ("openhardwaremonitor", False)],
    ids=["sections=openhardwaremonitor", "sections=openhardwaremonitor_systemtime"],
)
def testconfig_engine(request, make_yaml_config):
    Globals.alone = request.param[1]
    if Globals.alone:
        make_yaml_config["global"]["sections"] = request.param[0]
    else:
        make_yaml_config["global"]["sections"] = [request.param[0], "systemtime"]
    return make_yaml_config


@pytest.fixture
def wait_agent():
    def inner():
        # Wait a little so that OpenHardwareMonitorCLI.exe starts properly.
        time.sleep(10)
        return True

    return inner


@pytest.fixture(name="expected_output")
def expected_output_engine():
    re_str = (
        r"^\d+,[^,]+,(\/\w+)+,(Power|Clock|Load|Data|Temperature)," r"\d+\.\d{6},\b(?:OK|Timeout)\b"
    )
    if not Globals.alone:
        re_str += r"|" + re.escape(r"<<<systemtime>>>") + r"|\d+"
    re_str += r"$"
    return chain(
        [re.escape(r"<<<openhardwaremonitor:sep(44)>>>"), r"Index,Name,Parent,SensorType,Value"],
        repeat(re_str),
    )


@pytest.fixture(autouse=True)
def manage_ohm_binaries():
    if platform.system() == "Windows":
        binaries = ["OpenHardwareMonitorCLI.exe", "OpenHardwareMonitorLib.dll"]

        source_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "files\\ohm\cli"
        )
        target_dir = os.path.join(user_dir, "bin")

        it_utils.make_dir(target_dir)

        for f in binaries:
            shutil.copy(os.path.join(source_dir, f), target_dir)
    yield
    if platform.system() == "Windows":
        it_utils.stop_ohm()
        binaries.append("OpenHardwareMonitorLib.sys")
        it_utils.remove_files(target_dir, binaries)


def test_section_openhardwaremonitor(request, testconfig, expected_output, actual_output, testfile):
    required_lines = 2
    name = "openhardwaremonitor"

    if not it_utils.check_actual_input(name, required_lines, Globals.alone, actual_output):
        return

    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
