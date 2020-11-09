#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import re
import subprocess
from typing import List

import pytest  # type: ignore[import]

from testlib import web  # noqa: F401 # pylint: disable=unused-import
from testlib.utils import get_standard_linux_agent_output


@pytest.fixture(name="test_cfg", scope="module")
def test_cfg_fixture(web, site):  # noqa: F811 # pylint: disable=redefined-outer-name
    print("Applying default config")
    web.add_host("modes-test-host", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.add_host("modes-test-host2",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "tag_criticality": "test",
                 })
    web.add_host("modes-test-host3",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "tag_criticality": "test",
                 })
    web.add_host("modes-test-host4",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "tag_criticality": "offline",
                 })

    site.write_file(
        "etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ALL_HOSTS))\n")

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/modes-test-host", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host2", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host3", get_standard_linux_agent_output())

    web.discover_services("modes-test-host")
    web.discover_services("modes-test-host2")
    web.discover_services("modes-test-host3")

    web.activate_changes()
    yield None

    #
    # Cleanup code
    #
    print("Cleaning up test config")

    site.delete_dir("var/check_mk/agent_output")

    site.delete_file("etc/check_mk/conf.d/modes-test-host.mk")

    web.delete_host("modes-test-host")
    web.delete_host("modes-test-host2")
    web.delete_host("modes-test-host3")
    web.delete_host("modes-test-host4")

    web.activate_changes()


CommandOutput = collections.namedtuple('CommandOutput', [
    'returncode',
    'stdout',
    'stderr',
])


@pytest.fixture(name="execute")
def execute_fixture(test_cfg, site):
    def _execute(command, cwd=None):
        p = site.execute(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        stdout, stderr = p.communicate()
        return CommandOutput(returncode=p.returncode, stdout=stdout, stderr=stderr)

    return _execute


#.
#   .--General options-----------------------------------------------------.
#   |       ____                           _               _               |
#   |      / ___| ___ _ __   ___ _ __ __ _| |   ___  _ __ | |_ ___         |
#   |     | |  _ / _ \ '_ \ / _ \ '__/ _` | |  / _ \| '_ \| __/ __|        |
#   |     | |_| |  __/ | | |  __/ | | (_| | | | (_) | |_) | |_\__ \_       |
#   |      \____|\___|_| |_|\___|_|  \__,_|_|  \___/| .__/ \__|___(_)      |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--list-hosts----------------------------------------------------------.
#   |              _ _     _        _               _                      |
#   |             | (_)___| |_     | |__   ___  ___| |_ ___                |
#   |             | | / __| __|____| '_ \ / _ \/ __| __/ __|               |
#   |             | | \__ \ ||_____| | | | (_) \__ \ |_\__ \               |
#   |             |_|_|___/\__|    |_| |_|\___/|___/\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_list_hosts(execute):
    for opt in ["--list-hosts", "-l"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0
        assert p.stdout == "modes-test-host\nmodes-test-host2\nmodes-test-host3\n"


# TODO: add host to group and test the group filtering of --list-hosts

#.
#   .--list-tag------------------------------------------------------------.
#   |                   _ _     _        _                                 |
#   |                  | (_)___| |_     | |_ __ _  __ _                    |
#   |                  | | / __| __|____| __/ _` |/ _` |                   |
#   |                  | | \__ \ ||_____| || (_| | (_| |                   |
#   |                  |_|_|___/\__|     \__\__,_|\__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


def test_list_tag_all(execute):
    p = execute(["cmk", "--list-tag"])
    assert p.returncode == 0
    assert p.stdout == "modes-test-host\nmodes-test-host2\nmodes-test-host3\n"


def test_list_tag_single_tag_filter(execute):
    p = execute(["cmk", "--list-tag", "test"])
    assert p.returncode == 0
    assert p.stdout == "modes-test-host2\nmodes-test-host3\n"


def test_list_tag_offline(execute):
    p = execute(["cmk", "--list-tag", "offline"])
    assert p.returncode == 0
    assert p.stdout == "modes-test-host4\n"


def test_list_tag_multiple_tags(execute):
    p = execute(["cmk", "--list-tag", "test", "xyz"])
    assert p.returncode == 0
    assert p.stdout == ""


def test_list_tag_multiple_tags_2(execute):
    p = execute(["cmk", "--list-tag", "test", "cmk-agent"])
    assert p.returncode == 0
    assert p.stdout == "modes-test-host2\nmodes-test-host3\n"
    assert p.stderr == ''


#.
#   .--list-checks---------------------------------------------------------.
#   |           _ _     _             _               _                    |
#   |          | (_)___| |_       ___| |__   ___  ___| | _____             |
#   |          | | / __| __|____ / __| '_ \ / _ \/ __| |/ / __|            |
#   |          | | \__ \ ||_____| (__| | | |  __/ (__|   <\__ \            |
#   |          |_|_|___/\__|     \___|_| |_|\___|\___|_|\_\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_list_checks(execute):
    output_long = None
    for opt in ["--list-checks", "-L"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0
        assert p.stderr == ''
        assert "zypper" in p.stdout
        assert "Zypper: (Security) Updates" in p.stdout

        if output_long is None:
            output_long = p.stdout
        else:
            assert p.stdout == output_long


#.
#   .--dump-agent----------------------------------------------------------.
#   |        _                                                    _        |
#   |     __| |_   _ _ __ ___  _ __         __ _  __ _  ___ _ __ | |_      |
#   |    / _` | | | | '_ ` _ \| '_ \ _____ / _` |/ _` |/ _ \ '_ \| __|     |
#   |   | (_| | |_| | | | | | | |_) |_____| (_| | (_| |  __/ | | | |_      |
#   |    \__,_|\__,_|_| |_| |_| .__/       \__,_|\__, |\___|_| |_|\__|     |
#   |                         |_|                |___/                     |
#   '----------------------------------------------------------------------'


def test_dump_agent_missing_arg(execute):
    for opt in ["--dump-agent", "-d"]:
        p = execute(["cmk", opt])
        assert p.returncode == 1


def test_dump_agent_error(execute):
    output_long = None
    for opt in ["--dump-agent", "-d"]:
        p = execute(["cmk", opt, "modes-test-host4"])
        assert p.returncode == 1
        assert p.stdout == ""
        assert "[agent]: Agent exited " in p.stderr

        if output_long is None:
            output_long = p.stdout
        else:
            assert p.stdout == output_long


def test_dump_agent_test(execute):
    for opt in ["--dump-agent", "-d"]:
        p = execute(["cmk", opt, "modes-test-host"])
        assert p.returncode == 0
        assert p.stderr == ''
        assert p.stdout == get_standard_linux_agent_output()


#.
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_dump_agent_dump_all_hosts(execute):
    for opt in ["--dump", "-D"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0
        assert p.stderr == ''
        assert p.stdout.count("Addresses: ") == 3


def test_dump_agent(execute):
    for opt in ["--dump", "-D"]:
        p = execute(["cmk", opt, "modes-test-host"])
        assert p.returncode == 0
        assert p.stderr == ''
        assert "Addresses: " in p.stdout
        assert "Type of agent: " in p.stdout
        assert "Services:" in p.stdout


#.
#   .--paths---------------------------------------------------------------.
#   |                                  _   _                               |
#   |                      _ __   __ _| |_| |__  ___                       |
#   |                     | '_ \ / _` | __| '_ \/ __|                      |
#   |                     | |_) | (_| | |_| | | \__ \                      |
#   |                     | .__/ \__,_|\__|_| |_|___/                      |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


def test_paths(execute):
    p = execute(["cmk", "--paths"])
    assert p.returncode == 0
    assert p.stderr == ''
    assert "Main components of check_mk" in p.stdout
    assert "Locally installed " in p.stdout
    assert len(p.stdout.split("\n")) > 40


#.
#   .--backup/restore------------------------------------------------------.
#   |      _                _                  __             _            |
#   |     | |__   __ _  ___| | ___   _ _ __   / / __ ___  ___| |_          |
#   |     | '_ \ / _` |/ __| |/ / | | | '_ \ / / '__/ _ \/ __| __|         |
#   |     | |_) | (_| | (__|   <| |_| | |_) / /| | |  __/\__ \ |_ _        |
#   |     |_.__/ \__,_|\___|_|\_\\__,_| .__/_/ |_|  \___||___/\__(_)       |
#   |                                 |_|                                  |
#   '----------------------------------------------------------------------'


def _create_cmk_backup(site, execute):
    p = execute(["cmk", "--backup", "x.tgz"], cwd=site.root)
    assert p.returncode == 0, "Command failed: %r, %r" % (p.stdout, p.stderr)
    assert p.stderr == ''
    assert p.stdout == ""
    assert site.file_exists("x.tgz")


def test_backup(request, site, execute):
    def cleanup():
        site.delete_file("x.tgz")

    request.addfinalizer(cleanup)

    _create_cmk_backup(site, execute)


def test_restore(request, site, execute):
    # TODO: main.mk cannot be restored.
    def cleanup():
        if site.file_exists("etc/check_mk.sav"):
            site.delete_dir("etc/check_mk.sav")
        if site.file_exists("etc/check_mk/final.mk"):
            site.delete_file("etc/check_mk/final.mk")
        site.delete_file("x.tgz")

    request.addfinalizer(cleanup)

    # Add `final.mk` to the site, delete it, and restore it from a backup.
    assert execute(["cp", "etc/check_mk/main.mk", "etc/check_mk/final.mk"],
                   cwd=site.root).returncode == 0
    assert execute(["cp", "-pr", "etc/check_mk", "etc/check_mk.sav"], cwd=site.root).returncode == 0
    _create_cmk_backup(site, execute)

    site.delete_file("etc/check_mk/final.mk")
    p = execute(["cmk", "--restore", "x.tgz"], cwd=site.root)
    assert p.returncode == 0
    assert p.stderr == ''
    assert p.stdout == ""

    p = execute(["diff", "-ur", "etc/check_mk", "etc/check_mk.sav"], cwd=site.root)
    assert p.returncode == 0, "Found differences after restore: %s" % p.stdout


#.
#   .--package-------------------------------------------------------------.
#   |                                 _                                    |
#   |                _ __   __ _  ___| | ____ _  __ _  ___                 |
#   |               | '_ \ / _` |/ __| |/ / _` |/ _` |/ _ \                |
#   |               | |_) | (_| | (__|   < (_| | (_| |  __/                |
#   |               | .__/ \__,_|\___|_|\_\__,_|\__, |\___|                |
#   |               |_|                         |___/                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--localize------------------------------------------------------------.
#   |                    _                 _ _                             |
#   |                   | | ___   ___ __ _| (_)_______                     |
#   |                   | |/ _ \ / __/ _` | | |_  / _ \                    |
#   |                   | | (_) | (_| (_| | | |/ /  __/                    |
#   |                   |_|\___/ \___\__,_|_|_/___\___|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--config-check--------------------------------------------------------.
#   |                      __ _                  _               _         |
#   |      ___ ___  _ __  / _(_) __ _        ___| |__   ___  ___| | __     |
#   |     / __/ _ \| '_ \| |_| |/ _` |_____ / __| '_ \ / _ \/ __| |/ /     |
#   |    | (_| (_) | | | |  _| | (_| |_____| (__| | | |  __/ (__|   <      |
#   |     \___\___/|_| |_|_| |_|\__, |      \___|_| |_|\___|\___|_|\_\     |
#   |                           |___/                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--update-dns-cache----------------------------------------------------.
#   |                        _            _                                |
#   |        _   _ _ __   __| |        __| |_ __  ___        ___           |
#   |       | | | | '_ \ / _` | _____ / _` | '_ \/ __|_____ / __|          |
#   |       | |_| | |_) | (_| ||_____| (_| | | | \__ \_____| (__ _         |
#   |        \__,_| .__/ \__,_(_)     \__,_|_| |_|___/      \___(_)        |
#   |             |_|                                                      |
#   '----------------------------------------------------------------------'
# TODO

# TODO: --cleanup-piggyback

#.
#   .--scan-parents--------------------------------------------------------.
#   |                                                         _            |
#   |    ___  ___ __ _ _ __        _ __   __ _ _ __ ___ _ __ | |_ ___      |
#   |   / __|/ __/ _` | '_ \ _____| '_ \ / _` | '__/ _ \ '_ \| __/ __|     |
#   |   \__ \ (_| (_| | | | |_____| |_) | (_| | | |  __/ | | | |_\__ \     |
#   |   |___/\___\__,_|_| |_|     | .__/ \__,_|_|  \___|_| |_|\__|___/     |
#   |                             |_|                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--snmptranslate-------------------------------------------------------.
#   |                            _                       _       _         |
#   |  ___ _ __  _ __ ___  _ __ | |_ _ __ __ _ _ __  ___| | __ _| |_ ___   |
#   | / __| '_ \| '_ ` _ \| '_ \| __| '__/ _` | '_ \/ __| |/ _` | __/ _ \  |
#   | \__ \ | | | | | | | | |_) | |_| | | (_| | | | \__ \ | (_| | ||  __/  |
#   | |___/_| |_|_| |_| |_| .__/ \__|_|  \__,_|_| |_|___/_|\__,_|\__\___|  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--snmpwalk------------------------------------------------------------.
#   |                                                   _ _                |
#   |            ___ _ __  _ __ ___  _ ____      ____ _| | | __            |
#   |           / __| '_ \| '_ ` _ \| '_ \ \ /\ / / _` | | |/ /            |
#   |           \__ \ | | | | | | | | |_) \ V  V / (_| | |   <             |
#   |           |___/_| |_|_| |_| |_| .__/ \_/\_/ \__,_|_|_|\_\            |
#   |                               |_|                                    |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--snmpget-------------------------------------------------------------.
#   |                                                   _                  |
#   |              ___ _ __  _ __ ___  _ __   __ _  ___| |_                |
#   |             / __| '_ \| '_ ` _ \| '_ \ / _` |/ _ \ __|               |
#   |             \__ \ | | | | | | | | |_) | (_| |  __/ |_                |
#   |             |___/_| |_|_| |_| |_| .__/ \__, |\___|\__|               |
#   |                                 |_|    |___/                         |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--flush---------------------------------------------------------------.
#   |                         __ _           _                             |
#   |                        / _| |_   _ ___| |__                          |
#   |                       | |_| | | | / __| '_ \                         |
#   |                       |  _| | |_| \__ \ | | |                        |
#   |                       |_| |_|\__,_|___/_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_flush_existing_host(execute):
    p = execute(["cmk", "--flush", "modes-test-host4"])
    assert p.returncode == 0
    assert p.stderr == ''
    assert p.stdout == "modes-test-host4    : (nothing)\n"


def test_flush_not_existing_host(execute):
    p = execute(["cmk", "--flush", "bums"])
    assert p.returncode == 0
    assert p.stderr == ''
    assert p.stdout == "bums                : (nothing)\n"


#.
#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--restart-------------------------------------------------------------.
#   |                                 _             _                      |
#   |                   _ __ ___  ___| |_ __ _ _ __| |_                    |
#   |                  | '__/ _ \/ __| __/ _` | '__| __|                   |
#   |                  | | |  __/\__ \ || (_| | |  | |_                    |
#   |                  |_|  \___||___/\__\__,_|_|   \__|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--reload--------------------------------------------------------------.
#   |                             _                 _                      |
#   |                    _ __ ___| | ___   __ _  __| |                     |
#   |                   | '__/ _ \ |/ _ \ / _` |/ _` |                     |
#   |                   | | |  __/ | (_) | (_| | (_| |                     |
#   |                   |_|  \___|_|\___/ \__,_|\__,_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--man-----------------------------------------------------------------.
#   |                                                                      |
#   |                        _ __ ___   __ _ _ __                          |
#   |                       | '_ ` _ \ / _` | '_ \                         |
#   |                       | | | | | | (_| | | | |                        |
#   |                       |_| |_| |_|\__,_|_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--browse-man----------------------------------------------------------.
#   |    _                                                                 |
#   |   | |__  _ __ _____      _____  ___       _ __ ___   __ _ _ __       |
#   |   | '_ \| '__/ _ \ \ /\ / / __|/ _ \_____| '_ ` _ \ / _` | '_ \      |
#   |   | |_) | | | (_) \ V  V /\__ \  __/_____| | | | | | (_| | | | |     |
#   |   |_.__/|_|  \___/ \_/\_/ |___/\___|     |_| |_| |_|\__,_|_| |_|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--inventory-----------------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def test_inventory_all_hosts(execute):
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0
        assert p.stderr == ''
        assert p.stdout == ""


def test_inventory_single_host(execute):
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", opt, "modes-test-host"])
        assert p.returncode == 0
        assert p.stderr == ''
        assert p.stdout == ""


def test_inventory_multiple_hosts(execute):
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", opt, "modes-test-host", "modes-test-host2"])
        assert p.returncode == 0
        assert p.stderr == ''
        assert p.stdout == ""


def test_inventory_verbose(execute):
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", "-v", opt, "modes-test-host"])
        assert p.returncode == 0
        assert p.stderr == ''
        assert p.stdout.startswith("Doing HW/SW inventory on: modes-test-host\n")
        stdout_words = p.stdout.split()
        assert "check_mk" in stdout_words
        assert "lnx_if" in stdout_words
        assert "mem" in stdout_words


#.
#   .--inventory-as-check--------------------------------------------------.
#   | _                      _                              _     _        |
#   |(_)_ ____   _____ _ __ | |_ ___  _ __ _   _        ___| |__ | | __    |
#   || | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |_____ / __| '_ \| |/ /    |
#   || | | | \ V /  __/ | | | || (_) | |  | |_| |_____| (__| | | |   < _   |
#   ||_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |      \___|_| |_|_|\_(_)  |
#   |                                      |___/                           |
#   '----------------------------------------------------------------------'


def test_inventory_as_check_unknown_host(execute):
    p = execute(["cmk", "--inventory-as-check", "xyz."])
    assert p.returncode == 2
    assert p.stdout.startswith("CRIT - Failed to lookup IPv4 address of")
    assert p.stderr == ''


def test_inventory_as_check(execute):
    p = execute(["cmk", "--inventory-as-check", "modes-test-host"])
    assert p.returncode == 0
    assert re.match(r"OK - Found \d+ inventory entries", p.stdout)
    assert p.stderr == ''


#.
#   .--automation----------------------------------------------------------.
#   |                   _                        _   _                     |
#   |        __ _ _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __          |
#   |       / _` | | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \         |
#   |      | (_| | |_| | || (_) | | | | | | (_| | |_| | (_) | | | |        |
#   |       \__,_|\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--notify--------------------------------------------------------------.
#   |                                 _   _  __                            |
#   |                     _ __   ___ | |_(_)/ _|_   _                      |
#   |                    | '_ \ / _ \| __| | |_| | | |                     |
#   |                    | | | | (_) | |_| |  _| |_| |                     |
#   |                    |_| |_|\___/ \__|_|_|  \__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--discover-marked-hosts-----------------------------------------------.
#   |           _ _                                 _            _         |
#   |        __| (_)___  ___   _ __ ___   __ _ _ __| | _____  __| |        |
#   |       / _` | / __|/ __| | '_ ` _ \ / _` | '__| |/ / _ \/ _` |        |
#   |      | (_| | \__ \ (__ _| | | | | | (_| | |  |   <  __/ (_| |        |
#   |       \__,_|_|___/\___(_)_| |_| |_|\__,_|_|  |_|\_\___|\__,_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--check-discovery-----------------------------------------------------.
#   |       _     _               _ _                                      |
#   |   ___| |__ | | __        __| (_)___  ___ _____   _____ _ __ _   _    |
#   |  / __| '_ \| |/ / _____ / _` | / __|/ __/ _ \ \ / / _ \ '__| | | |   |
#   | | (__| | | |   < |_____| (_| | \__ \ (_| (_) \ V /  __/ |  | |_| |   |
#   |  \___|_| |_|_|\_(_)     \__,_|_|___/\___\___/ \_/ \___|_|   \__, |   |
#   |                                                             |___/    |
#   '----------------------------------------------------------------------'


def test_check_discovery_host(execute):
    p = execute(["cmk", "--check-discovery", "xyz."])
    assert p.returncode == 2
    assert p.stdout.startswith("CRIT - Failed to lookup IPv4 address")
    assert p.stderr == ''


def test_check_discovery(execute):
    p = execute(["cmk", "--check-discovery", "modes-test-host"])
    assert p.returncode == 0
    assert p.stdout.startswith("OK - ")
    assert p.stderr == ''


#.
#   .--discover------------------------------------------------------------.
#   |                     _ _                                              |
#   |                  __| (_)___  ___ _____   _____ _ __                  |
#   |                 / _` | / __|/ __/ _ \ \ / / _ \ '__|                 |
#   |                | (_| | \__ \ (_| (_) \ V /  __/ |                    |
#   |                 \__,_|_|___/\___\___/ \_/ \___|_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--check---------------------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_check(execute):
    opts: List[List[str]] = [["--check"], []]
    for opt in opts:
        p = execute(["cmk"] + opt + ["modes-test-host"])
        assert p.returncode == 0
        assert p.stdout.startswith("OK - [agent] Version:")


def test_check_verbose_perfdata(execute):
    p = execute(["cmk", "-v", "-p", "modes-test-host"])
    assert p.returncode == 0
    assert "Temperature Zone 0" in p.stdout
    assert "temp=32.4;" in p.stdout
    assert "OK - [agent] Version:" in p.stdout


def test_check_verbose_only_check(execute):
    p = execute(["cmk", "-v", "--checks=lnx_thermal", "modes-test-host"])
    assert p.returncode == 0
    assert "Temperature Zone 0" in p.stdout
    assert "Interface 2" not in p.stdout
    assert "OK - [agent] Version:" in p.stdout


#.
#   .--version-------------------------------------------------------------.
#   |                                     _                                |
#   |                 __   _____ _ __ ___(_) ___  _ __                     |
#   |                 \ \ / / _ \ '__/ __| |/ _ \| '_ \                    |
#   |                  \ V /  __/ |  \__ \ | (_) | | | |                   |
#   |                   \_/ \___|_|  |___/_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_version(execute):
    p = execute(["cmk", "--version"])
    assert p.returncode == 0
    assert p.stderr == ""
    assert "This is Check_MK" in p.stdout


#.
#   .--help----------------------------------------------------------------.
#   |                         _          _                                 |
#   |                        | |__   ___| |_ __                            |
#   |                        | '_ \ / _ \ | '_ \                           |
#   |                        | | | |  __/ | |_) |                          |
#   |                        |_| |_|\___|_| .__/                           |
#   |                                     |_|                              |
#   '----------------------------------------------------------------------'


def test_help(execute):
    p = execute(["cmk", "--help"])
    assert p.returncode == 0
    assert p.stderr == ""
    assert p.stdout.startswith("WAYS TO CALL:")
    assert "--snmpwalk" in p.stdout


def test_help_without_args(execute):
    p = execute(["cmk"])
    assert p.returncode == 0
    assert p.stderr == ''
    assert p.stdout.startswith("WAYS TO CALL:")
    assert "--snmpwalk" in p.stdout


#.
#   .--diagnostics---------------------------------------------------------.
#   |             _ _                             _   _                    |
#   |          __| (_) __ _  __ _ _ __   ___  ___| |_(_) ___ ___           |
#   |         / _` | |/ _` |/ _` | '_ \ / _ \/ __| __| |/ __/ __|          |
#   |        | (_| | | (_| | (_| | | | | (_) \__ \ |_| | (__\__ \          |
#   |         \__,_|_|\__,_|\__, |_| |_|\___/|___/\__|_|\___|___/          |
#   |                       |___/                                          |
#   '----------------------------------------------------------------------'


def test_create_diagnostics_dump(execute):
    p = execute(["cmk", "--create-diagnostics-dump"])
    assert p.returncode == 0
    assert p.stderr == ""
    assert p.stdout.startswith("+ COLLECT DIAGNOSTICS INFORMATION")
