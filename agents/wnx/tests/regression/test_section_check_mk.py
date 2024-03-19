#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re

import pytest

from .local import get_main_yaml_name, get_user_yaml_name, local_test, root_dir, user_dir


class Globals:
    section = "check_mk"
    alone = True
    output_file = "agentoutput.txt"
    only_from: str | None = None
    ipv4_to_ipv6 = {"127.0.0.1": "0:0:0:0:0:ffff:7f00:1", "10.1.2.3": "0:0:0:0:0:ffff:a01:203"}


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
    return make_yaml_config


@pytest.fixture(name="testconfig_host")
def testconfig_host_engine(testconfig):
    return testconfig


@pytest.fixture(
    name="testconfig_only_from",
    params=[None, "127.0.0.1 10.1.2.3"],
    ids=["only_from=None", "only_from=127.0.0.1_10.1.2.3"],
)
def testconfig_only_from_engine(request, testconfig_host):
    Globals.only_from = request.param
    if request.param:
        testconfig_host["global"]["only_from"] = ["127.0.0.1", "10.1.2.3"]
    else:
        testconfig_host["global"]["only_from"] = None
    return testconfig_host


# live example of valid output
_EXAMPLE = """
<<<check_mk>>>
Version: 2.3.0-2024.03.15
BuildDate: Mar 15 2024
AgentOS: windows
Hostname: klapp-0336
Architecture: 64bit
OSName: Microsoft Windows 10 Pro
OSVersion: 10.0.19045
OSType: windows
Time: 2024-03-19T13:42:18+0100
WorkingDirectory: c:\\dev\\shared
ConfigFile: c:\\dev\\shared\\check_mk.yml
LocalConfigFile: C:\\ProgramData\\checkmk\\agent\\check_mk.user.yml
AgentDirectory: c:\\dev\\shared
PluginsDirectory: C:\\ProgramData\\checkmk\\agent\\plugins
StateDirectory: C:\\ProgramData\\checkmk\\agent\\state
ConfigDirectory: C:\\ProgramData\\checkmk\\agent\\config
TempDirectory: C:\\ProgramData\\checkmk\\agent\\tmp
LogDirectory: C:\\ProgramData\\checkmk\\agent\\log
SpoolDirectory: C:\\ProgramData\\checkmk\\agent\\spool
LocalDirectory: C:\\ProgramData\\checkmk\\agent\\local
OnlyFrom: 0.0.0.0/0
<<<cmk_agent_ctl_status:sep(0)>>>:
"""


def make_only_from_array(ipv4):
    if ipv4 is None:
        return None

    addr_list = []

    # not very pythonic, but other methods(reduce) overkill
    for x in ipv4:
        addr_list.append(x)
        # addr_list.append(Globals.ipv4_to_ipv6[x])

    return addr_list


@pytest.fixture(name="expected_output")
def expected_output_engine():
    ipv4 = Globals.only_from.split() if Globals.only_from is not None else None
    expected = [
        r"<<<%s>>>" % Globals.section,
        r"Version: \d+\.\d+\.\d+([bi]\d+)?(p\d+)?",
        r"BuildDate: [A-Z][a-z]{2} (\d{2}| \d) \d{4}",
        r"AgentOS: windows",
        r"Hostname: .+",
        r"Architecture: \d{2}bit",
        r"OSName: Microsoft .+",
        r"OSVersion: 10.+",
        r"OSType: windows",
        r"Time: 20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d[\+,-]\d\d\d\d",
        r"WorkingDirectory: %s" % (re.escape(os.getcwd())),
        r"ConfigFile: %s" % (re.escape(get_main_yaml_name(root_dir))),
        r"LocalConfigFile: %s" % (re.escape(get_user_yaml_name(user_dir))),
        r"AgentDirectory: %s" % (re.escape(str(root_dir))),
        r"PluginsDirectory: %s" % (re.escape(os.path.join(user_dir, "plugins"))),
        r"StateDirectory: %s" % (re.escape(os.path.join(user_dir, "state"))),
        r"ConfigDirectory: %s" % (re.escape(os.path.join(user_dir, "config"))),
        r"TempDirectory: %s" % (re.escape(os.path.join(user_dir, "tmp"))),
        r"LogDirectory: %s" % (re.escape(os.path.join(user_dir, "log"))),
        r"SpoolDirectory: %s" % (re.escape(os.path.join(user_dir, "spool"))),
        r"LocalDirectory: %s" % (re.escape(os.path.join(user_dir, "local"))),
        (
            r"OnlyFrom: %s %s" % tuple(make_only_from_array(ipv4))
            if Globals.only_from
            else r"OnlyFrom: "
        ),
        r"<<<cmk_agent_ctl_status:sep(0)>>>",
    ]
    if not Globals.alone:
        expected += [re.escape(r"<<<systemtime>>>"), r"\d+"]
    return expected


def test_section_check_mk(  # type: ignore[no-untyped-def]
    request, testconfig_only_from, expected_output, actual_output, testfile
) -> None:
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
