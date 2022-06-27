#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import platform
import re
import shutil

import pytest

from .local import local_test, user_dir


class Globals:
    section = "mrpe"
    alone = True
    pluginname = "check_crit.bat"
    param = "foobar"
    checkname = "Dummy"
    mrpedir = "mrpe"
    includedir = "test include"  # space in directory name!
    cfgfile = "test.cfg"
    newline = -1


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(name="testconfig", params=["alone", "with_systemtime"])
def testconfig_engine(request, make_yaml_config):
    Globals.alone = request.param == "alone"
    if Globals.alone:
        make_yaml_config["global"]["sections"] = Globals.section
    else:
        make_yaml_config["global"]["sections"] = [Globals.section, "systemtime"]

    if Globals.newline < 0:
        make_yaml_config["mrpe"] = {
            "enabled": "yes",
            "timeout": 60,
            "config": [
                "check = %s '%s'"
                % (Globals.checkname, os.path.join(Globals.mrpedir, Globals.pluginname))
            ],
        }
    else:
        make_yaml_config["mrpe"] = {
            "enabled": "yes",
            "timeout": 60,
            "config": ["include = '%s'" % os.path.join(Globals.includedir, Globals.cfgfile)],
        }
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    expected = [
        re.escape(r"<<<%s>>>" % Globals.section),
        r"\(%s\) %s 2 CRIT - This check is always critical"
        % (Globals.pluginname, Globals.checkname),
    ]
    if not Globals.alone:
        expected += [re.escape(r"<<<systemtime>>>"), r"\d+"]
    return expected


@pytest.fixture(
    params=[-1, 0, 1, 2],
    ids=[
        "direct",
        "include_without_newline",
        "include_with_newline",
        "include_with_newline_forward_slash",
    ],
    autouse=True,
)
def manage_plugin(request):
    Globals.newline = request.param
    plugin_dir = Globals.mrpedir if Globals.newline < 0 else Globals.includedir
    source_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "files\\regression"
    )
    target_dir = os.path.join(user_dir, plugin_dir)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    shutil.copy(os.path.join(source_dir, Globals.pluginname), target_dir)

    # create config file
    if Globals.newline >= 0:
        with open(os.path.join(target_dir, Globals.cfgfile), "wb") as cfg:
            path = os.path.join(target_dir, Globals.pluginname)
            if Globals.newline == 2:
                path = path.replace("\\", "/")
            cfg_line = "check = %s '%s'%s" % (
                Globals.checkname,
                path,
                "\n" if Globals.newline > 0 else "",
            )
            cfg.write(str.encode(cfg_line))
    yield
    if platform.system() == "Windows":
        os.unlink(os.path.join(target_dir, Globals.pluginname))
        if Globals.newline >= 0:
            os.unlink(os.path.join(target_dir, Globals.cfgfile))


def test_section_mrpe(request, testconfig, expected_output, actual_output, testfile) -> None:
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
