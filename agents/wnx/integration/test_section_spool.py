#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import platform
import re

import pytest  # type: ignore[import]

from .local import local_test, user_dir


class Globals:
    section = "spool"
    alone = True
    test_message = "Test message"
    outdated = False


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(name="testconfig", params=["alone", "with_systemtime"])
def testconfig(request, make_yaml_config):
    Globals.alone = request.param == "alone"
    if Globals.alone:
        make_yaml_config["global"]["sections"] = Globals.section
    else:
        make_yaml_config["global"]["sections"] = [Globals.section, "systemtime"]
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    expected = []
    if not Globals.outdated:
        expected += [r"%s" % Globals.test_message]
    if not Globals.alone:
        expected += [re.escape(r"<<<systemtime>>>"), r"\d+"]
    return expected


@pytest.fixture(params=["yes", "no"], ids=["outdated", "not_outdated"], autouse=True)
def manage_spoolfile(request):
    Globals.outdated = request.param == "yes"
    testfile = "0testfile" if request.param == "yes" else "testfile"
    filename = os.path.join(user_dir, "spool", testfile)
    if platform.system() == "Windows":
        spooldir = os.path.join(user_dir, "spool")
        try:
            os.mkdir(spooldir)
        except OSError:
            pass  # Directory may already exist.
        with open(filename, "w") as f:
            f.write("%s" % Globals.test_message)
        # Hack the modification time 2 s back in time
        stat = os.stat(filename)
        times = stat.st_atime, stat.st_mtime - 2
        os.utime(filename, times)

    yield

    if platform.system() == "Windows":
        os.unlink(filename)


def test_section_spool(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
