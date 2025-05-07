#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import subprocess
from collections.abc import Callable, Iterator
from typing import NamedTuple

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_standard_linux_agent_output

logger = logging.getLogger(__name__)


@pytest.fixture(name="test_cfg", scope="module")
def test_cfg_fixture(site: Site) -> Iterator[None]:
    logger.info("Applying default config")
    site.openapi.hosts.create(
        "modes-test-host",
        attributes={
            "ipaddress": "127.0.0.1",
        },
    )
    site.openapi.hosts.create(
        "modes-test-host2",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
    )
    site.openapi.hosts.create(
        "modes-test-host3",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
    )
    site.openapi.hosts.create(
        "modes-test-host4",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "offline",
        },
    )

    site.write_file(
        "etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append({'condition': {}, 'value': 'cat ~/var/check_mk/agent_output/<HOST>'})\n",
    )

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/modes-test-host", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host2", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host3", get_standard_linux_agent_output())

    site.openapi.service_discovery.run_discovery_and_wait_for_completion("modes-test-host")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion("modes-test-host2")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion("modes-test-host3")

    try:
        site.activate_changes_and_wait_for_core_reload()
        yield None
    finally:
        #
        # Cleanup code
        #
        logger.info("Cleaning up test config")

        site.delete_dir("var/check_mk/agent_output")

        site.delete_file("etc/check_mk/conf.d/modes-test-host.mk")

        site.openapi.hosts.delete("modes-test-host")
        site.openapi.hosts.delete("modes-test-host2")
        site.openapi.hosts.delete("modes-test-host3")
        site.openapi.hosts.delete("modes-test-host4")

        site.activate_changes_and_wait_for_core_reload()


class CommandOutput(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


def on_failure(p: CommandOutput) -> str:
    return f"Command failed ({p.stdout!r}, {p.stderr!r})"


Execute = Callable[[list[str]], CommandOutput]


@pytest.fixture(name="execute")
def execute_fixture(test_cfg: None, site: Site) -> Execute:
    def _execute(command: list[str]) -> CommandOutput:
        p = site.execute(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=None)
        stdout, stderr = p.communicate()
        return CommandOutput(returncode=p.returncode, stdout=stdout, stderr=stderr)

    return _execute


# .
#   .--General options-----------------------------------------------------.
#   |       ____                           _               _               |
#   |      / ___| ___ _ __   ___ _ __ __ _| |   ___  _ __ | |_ ___         |
#   |     | |  _ / _ \ '_ \ / _ \ '__/ _` | |  / _ \| '_ \| __/ __|        |
#   |     | |_| |  __/ | | |  __/ | | (_| | | | (_) | |_) | |_\__ \_       |
#   |      \____|\___|_| |_|\___|_|  \__,_|_|  \___/| .__/ \__|___(_)      |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--list-hosts----------------------------------------------------------.
#   |              _ _     _        _               _                      |
#   |             | (_)___| |_     | |__   ___  ___| |_ ___                |
#   |             | | / __| __|____| '_ \ / _ \/ __| __/ __|               |
#   |             | | \__ \ ||_____| | | | (_) \__ \ |_\__ \               |
#   |             |_|_|___/\__|    |_| |_|\___/|___/\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_list_hosts(execute: Execute) -> None:
    for opt in ["--list-hosts", "-l"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0, on_failure(p)
        assert p.stdout == "modes-test-host\nmodes-test-host2\nmodes-test-host3\n"


# TODO: add host to group and test the group filtering of --list-hosts

# .
#   .--list-tag------------------------------------------------------------.
#   |                   _ _     _        _                                 |
#   |                  | (_)___| |_     | |_ __ _  __ _                    |
#   |                  | | / __| __|____| __/ _` |/ _` |                   |
#   |                  | | \__ \ ||_____| || (_| | (_| |                   |
#   |                  |_|_|___/\__|     \__\__,_|\__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


def test_list_tag_all(execute: Execute) -> None:
    p = execute(["cmk", "--list-tag"])
    assert p.returncode == 0, on_failure(p)
    assert p.stdout == "modes-test-host\nmodes-test-host2\nmodes-test-host3\n"


def test_list_tag_single_tag_filter(execute: Execute) -> None:
    p = execute(["cmk", "--list-tag", "test"])
    assert p.returncode == 0, on_failure(p)
    assert p.stdout == "modes-test-host2\nmodes-test-host3\n"


def test_list_tag_offline(execute: Execute) -> None:
    p = execute(["cmk", "--list-tag", "offline"])
    assert p.returncode == 0, on_failure(p)
    assert p.stdout == "modes-test-host4\n"


def test_list_tag_multiple_tags(execute: Execute) -> None:
    p = execute(["cmk", "--list-tag", "test", "xyz"])
    assert p.returncode == 0, on_failure(p)
    assert p.stdout == ""


def test_list_tag_multiple_tags_2(execute: Execute) -> None:
    p = execute(["cmk", "--list-tag", "test", "cmk-agent"])
    assert p.returncode == 0, on_failure(p)
    assert p.stdout == "modes-test-host2\nmodes-test-host3\n"
    assert p.stderr == ""


# .
#   .--list-checks---------------------------------------------------------.
#   |           _ _     _             _               _                    |
#   |          | (_)___| |_       ___| |__   ___  ___| | _____             |
#   |          | | / __| __|____ / __| '_ \ / _ \/ __| |/ / __|            |
#   |          | | \__ \ ||_____| (__| | | |  __/ (__|   <\__ \            |
#   |          |_|_|___/\__|     \___|_| |_|\___|\___|_|\_\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_list_checks(execute: Execute) -> None:
    output_long = None
    for opt in ["--list-checks", "-L"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert "zypper" in p.stdout
        assert "Zypper: (Security) Updates" in p.stdout

        if output_long is None:
            output_long = p.stdout
        else:
            assert p.stdout == output_long


# .
#   .--dump-agent----------------------------------------------------------.
#   |        _                                                    _        |
#   |     __| |_   _ _ __ ___  _ __         __ _  __ _  ___ _ __ | |_      |
#   |    / _` | | | | '_ ` _ \| '_ \ _____ / _` |/ _` |/ _ \ '_ \| __|     |
#   |   | (_| | |_| | | | | | | |_) |_____| (_| | (_| |  __/ | | | |_      |
#   |    \__,_|\__,_|_| |_| |_| .__/       \__,_|\__, |\___|_| |_|\__|     |
#   |                         |_|                |___/                     |
#   '----------------------------------------------------------------------'


def test_dump_agent_missing_arg(execute: Execute) -> None:
    for opt in ["--dump-agent", "-d"]:
        p = execute(["cmk", opt])
        assert p.returncode == 1, on_failure(p)


def test_dump_agent_error(execute: Execute) -> None:
    output_long = None
    for opt in ["--dump-agent", "-d"]:
        p = execute(["cmk", opt, "modes-test-host4"])
        assert p.returncode == 1, on_failure(p)
        assert p.stdout == ""
        assert "[agent]: Agent exited " in p.stderr

        if output_long is None:
            output_long = p.stdout
        else:
            assert p.stdout == output_long


def test_dump_agent_test(execute: Execute) -> None:
    for opt in ["--dump-agent", "-d"]:
        p = execute(["cmk", opt, "modes-test-host"])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert p.stdout == get_standard_linux_agent_output()


# .
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_dump_agent_dump_all_hosts(execute: Execute) -> None:
    for opt in ["--dump", "-D"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert p.stdout.count("Addresses: ") == 3


def test_dump_agent(execute: Execute) -> None:
    for opt in ["--dump", "-D"]:
        p = execute(["cmk", opt, "modes-test-host"])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert "Addresses: " in p.stdout
        assert "Type of agent: " in p.stdout
        assert "Services:" in p.stdout


# .
#   .--localize------------------------------------------------------------.
#   |                    _                 _ _                             |
#   |                   | | ___   ___ __ _| (_)_______                     |
#   |                   | |/ _ \ / __/ _` | | |_  / _ \                    |
#   |                   | | (_) | (_| (_| | | |/ /  __/                    |
#   |                   |_|\___/ \___\__,_|_|_/___\___|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--config-check--------------------------------------------------------.
#   |                      __ _                  _               _         |
#   |      ___ ___  _ __  / _(_) __ _        ___| |__   ___  ___| | __     |
#   |     / __/ _ \| '_ \| |_| |/ _` |_____ / __| '_ \ / _ \/ __| |/ /     |
#   |    | (_| (_) | | | |  _| | (_| |_____| (__| | | |  __/ (__|   <      |
#   |     \___\___/|_| |_|_| |_|\__, |      \___|_| |_|\___|\___|_|\_\     |
#   |                           |___/                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
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

# .
#   .--snmptranslate-------------------------------------------------------.
#   |                            _                       _       _         |
#   |  ___ _ __  _ __ ___  _ __ | |_ _ __ __ _ _ __  ___| | __ _| |_ ___   |
#   | / __| '_ \| '_ ` _ \| '_ \| __| '__/ _` | '_ \/ __| |/ _` | __/ _ \  |
#   | \__ \ | | | | | | | | |_) | |_| | | (_| | | | \__ \ | (_| | ||  __/  |
#   | |___/_| |_|_| |_| |_| .__/ \__|_|  \__,_|_| |_|___/_|\__,_|\__\___|  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--snmpwalk------------------------------------------------------------.
#   |                                                   _ _                |
#   |            ___ _ __  _ __ ___  _ ____      ____ _| | | __            |
#   |           / __| '_ \| '_ ` _ \| '_ \ \ /\ / / _` | | |/ /            |
#   |           \__ \ | | | | | | | | |_) \ V  V / (_| | |   <             |
#   |           |___/_| |_|_| |_| |_| .__/ \_/\_/ \__,_|_|_|\_\            |
#   |                               |_|                                    |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--snmpget-------------------------------------------------------------.
#   |                                                   _                  |
#   |              ___ _ __  _ __ ___  _ __   __ _  ___| |_                |
#   |             / __| '_ \| '_ ` _ \| '_ \ / _` |/ _ \ __|               |
#   |             \__ \ | | | | | | | | |_) | (_| |  __/ |_                |
#   |             |___/_| |_|_| |_| |_| .__/ \__, |\___|\__|               |
#   |                                 |_|    |___/                         |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--flush---------------------------------------------------------------.
#   |                         __ _           _                             |
#   |                        / _| |_   _ ___| |__                          |
#   |                       | |_| | | | / __| '_ \                         |
#   |                       |  _| | |_| \__ \ | | |                        |
#   |                       |_| |_|\__,_|___/_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_flush_existing_host(execute: Execute) -> None:
    p = execute(["cmk", "--flush", "modes-test-host4"])
    assert p.returncode == 0, on_failure(p)
    assert p.stderr == ""
    assert p.stdout == "modes-test-host4    : (nothing)\n"


def test_flush_not_existing_host(execute: Execute) -> None:
    p = execute(["cmk", "--flush", "bums"])
    assert p.returncode == 0, on_failure(p)
    assert p.stderr == ""
    assert p.stdout == "bums                : (nothing)\n"


# .
#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--restart-------------------------------------------------------------.
#   |                                 _             _                      |
#   |                   _ __ ___  ___| |_ __ _ _ __| |_                    |
#   |                  | '__/ _ \/ __| __/ _` | '__| __|                   |
#   |                  | | |  __/\__ \ || (_| | |  | |_                    |
#   |                  |_|  \___||___/\__\__,_|_|   \__|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--reload--------------------------------------------------------------.
#   |                             _                 _                      |
#   |                    _ __ ___| | ___   __ _  __| |                     |
#   |                   | '__/ _ \ |/ _ \ / _` |/ _` |                     |
#   |                   | | |  __/ | (_) | (_| | (_| |                     |
#   |                   |_|  \___|_|\___/ \__,_|\__,_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--man-----------------------------------------------------------------.
#   |                                                                      |
#   |                        _ __ ___   __ _ _ __                          |
#   |                       | '_ ` _ \ / _` | '_ \                         |
#   |                       | | | | | | (_| | | | |                        |
#   |                       |_| |_| |_|\__,_|_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--browse-man----------------------------------------------------------.
#   |    _                                                                 |
#   |   | |__  _ __ _____      _____  ___       _ __ ___   __ _ _ __       |
#   |   | '_ \| '__/ _ \ \ /\ / / __|/ _ \_____| '_ ` _ \ / _` | '_ \      |
#   |   | |_) | | | (_) \ V  V /\__ \  __/_____| | | | | | (_| | | | |     |
#   |   |_.__/|_|  \___/ \_/\_/ |___/\___|     |_| |_| |_|\__,_|_| |_|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--inventory-----------------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def test_inventory_all_hosts(execute: Execute) -> None:
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", opt])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert p.stdout == ""


def test_inventory_single_host(execute: Execute) -> None:
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", opt, "modes-test-host"])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert p.stdout == ""


def test_inventory_multiple_hosts(execute: Execute) -> None:
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", opt, "modes-test-host", "modes-test-host2"])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert p.stdout == ""


def test_inventory_verbose(execute: Execute) -> None:
    for opt in ["--inventory", "-i"]:
        p = execute(["cmk", "-v", opt, "modes-test-host"])
        assert p.returncode == 0, on_failure(p)
        assert p.stderr == ""
        assert p.stdout.startswith("Doing HW/SW Inventory on: modes-test-host\n")
        stdout_words = p.stdout.split()
        for expected_word in ("check_mk:", "lnx_if:", "mem:"):
            assert expected_word in stdout_words
            assert stdout_words[stdout_words.index(expected_word) + 1] == "ok"


# .
#   .--automation----------------------------------------------------------.
#   |                   _                        _   _                     |
#   |        __ _ _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __          |
#   |       / _` | | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \         |
#   |      | (_| | |_| | || (_) | | | | | | (_| | |_| | (_) | | | |        |
#   |       \__,_|\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--notify--------------------------------------------------------------.
#   |                                 _   _  __                            |
#   |                     _ __   ___ | |_(_)/ _|_   _                      |
#   |                    | '_ \ / _ \| __| | |_| | | |                     |
#   |                    | | | | (_) | |_| |  _| |_| |                     |
#   |                    |_| |_|\___/ \__|_|_|  \__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--check-discovery-----------------------------------------------------.
#   |       _     _               _ _                                      |
#   |   ___| |__ | | __        __| (_)___  ___ _____   _____ _ __ _   _    |
#   |  / __| '_ \| |/ / _____ / _` | / __|/ __/ _ \ \ / / _ \ '__| | | |   |
#   | | (__| | | |   < |_____| (_| | \__ \ (_| (_) \ V /  __/ |  | |_| |   |
#   |  \___|_| |_|_|\_(_)     \__,_|_|___/\___\___/ \_/ \___|_|   \__, |   |
#   |                                                             |___/    |
#   '----------------------------------------------------------------------'


def test_check_discovery_host(execute: Execute) -> None:
    p = execute(["cmk", "--check-discovery", "xyz."])
    assert p.returncode == 2, on_failure(p)
    assert p.stdout.startswith("Failed to lookup IPv4 address")
    assert p.stderr == ""


def test_check_discovery(execute: Execute) -> None:
    p = execute(["cmk", "--check-discovery", "modes-test-host"])
    assert p.returncode == 0, on_failure(p)
    assert p.stdout.startswith("Services: all up to date, Host labels: all up to date")
    assert p.stderr == ""


# .
#   .--discover------------------------------------------------------------.
#   |                     _ _                                              |
#   |                  __| (_)___  ___ _____   _____ _ __                  |
#   |                 / _` | / __|/ __/ _ \ \ / / _ \ '__|                 |
#   |                | (_| | \__ \ (_| (_) \ V /  __/ |                    |
#   |                 \__,_|_|___/\___\___/ \_/ \___|_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

# .
#   .--check---------------------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_check(execute: Execute) -> None:
    opts: list[list[str]] = [["--check"], []]
    for opt in opts:
        p = execute(["cmk"] + opt + ["modes-test-host"])
        assert p.returncode == 0, on_failure(p)
        assert p.stdout.startswith("[agent] Success")


def test_check_verbose_perfdata(execute: Execute) -> None:
    p = execute(["cmk", "-v", "-p", "modes-test-host"])
    assert p.returncode == 0, on_failure(p)
    assert "Temperature Zone 0" in p.stdout
    assert "temp=32.4;" in p.stdout
    assert "[agent] Success" in p.stdout


def test_check_verbose_only_check(execute: Execute) -> None:
    p = execute(["cmk", "-v", "--plugins=lnx_thermal", "modes-test-host"])
    assert p.returncode == 0, on_failure(p)
    assert "Temperature Zone 0" in p.stdout
    assert "Interface 2" not in p.stdout
    assert "[agent] Success" in p.stdout


# .
#   .--version-------------------------------------------------------------.
#   |                                     _                                |
#   |                 __   _____ _ __ ___(_) ___  _ __                     |
#   |                 \ \ / / _ \ '__/ __| |/ _ \| '_ \                    |
#   |                  \ V /  __/ |  \__ \ | (_) | | | |                   |
#   |                   \_/ \___|_|  |___/_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_version(execute: Execute) -> None:
    p = execute(["cmk", "--version"])
    assert p.returncode == 0, on_failure(p)
    assert p.stderr == ""
    assert "This is Check_MK" in p.stdout


# .
#   .--help----------------------------------------------------------------.
#   |                         _          _                                 |
#   |                        | |__   ___| |_ __                            |
#   |                        | '_ \ / _ \ | '_ \                           |
#   |                        | | | |  __/ | |_) |                          |
#   |                        |_| |_|\___|_| .__/                           |
#   |                                     |_|                              |
#   '----------------------------------------------------------------------'


def test_help(execute: Execute) -> None:
    p = execute(["cmk", "--help"])
    assert p.returncode == 0, on_failure(p)
    assert p.stderr == ""
    assert p.stdout.startswith("WAYS TO CALL:")
    assert "--snmpwalk" in p.stdout


def test_help_without_args(execute: Execute) -> None:
    p = execute(["cmk"])
    assert p.returncode == 0, on_failure(p)
    assert p.stderr == ""
    assert p.stdout.startswith("WAYS TO CALL:")
    assert "--snmpwalk" in p.stdout


# .
#   .--diagnostics---------------------------------------------------------.
#   |             _ _                             _   _                    |
#   |          __| (_) __ _  __ _ _ __   ___  ___| |_(_) ___ ___           |
#   |         / _` | |/ _` |/ _` | '_ \ / _ \/ __| __| |/ __/ __|          |
#   |        | (_| | | (_| | (_| | | | | (_) \__ \ |_| | (__\__ \          |
#   |         \__,_|_|\__,_|\__, |_| |_|\___/|___/\__|_|\___|___/          |
#   |                       |___/                                          |
#   '----------------------------------------------------------------------'


def test_create_diagnostics_dump(execute: Execute) -> None:
    p = execute(["cmk", "--create-diagnostics-dump"])
    assert p.returncode == 0, on_failure(p)
    assert p.stderr == ""
    assert p.stdout.startswith("+ COLLECT DIAGNOSTICS INFORMATION")
