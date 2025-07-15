#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

import pytest

from tests.integration.linux_test_host import create_linux_test_host

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

from cmk.checkengine.discovery._autochecks import _AutochecksSerializer


def test_test_check_1_merged_rule(request: pytest.FixtureRequest, site: Site) -> None:
    host_name = "disco-params-test-host"

    create_linux_test_host(request, site, host_name)
    site.write_file(f"var/check_mk/agent_output/{host_name}", "<<<test_check_1>>>\n1 2\n")

    test_check_dir = "local/lib/python3/cmk/plugins/collection/agent_based"
    test_check_path = f"{test_check_dir}/test_check_1.py"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_1.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_1.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.makedirs(test_check_dir)
    site.write_file(
        test_check_path,
        """
import pprint

from cmk.agent_based.v2 import Service, CheckPlugin, RuleSetType


def discover(params, section):
    yield Service(item=pprint.pformat(params))


def check(item, section):
    return
    yield


check_plugin_test_check_1 = CheckPlugin(
    name="test_check_1",
    discovery_function=discover,
    discovery_ruleset_name="discover_test_check_1",
    discovery_ruleset_type=RuleSetType.MERGED,
    discovery_default_parameters={"default": 42},
    check_function=check,
    service_name="Foo %s",
)
""",
    )

    site.activate_changes_and_wait_for_core_reload()
    _restart_automation_helpers_and_wait_until_reachable(site)

    site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)

    # Verify that the discovery worked as expected
    entries = _AutochecksSerializer().deserialize(
        site.read_file(f"var/check_mk/autochecks/{host_name}.mk").encode("utf-8")
    )
    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_1":
            assert entry.item == "Parameters({'default': 42})"
            break
    else:
        raise AssertionError('"test_check_1" not discovered')

    # And now overwrite the setting in the config
    site.write_file(
        "etc/check_mk/conf.d/test_check_1.mk",
        "discover_test_check_1 = [{'value': {'levels': (1, 2)}, 'condition': {}}]\n",
    )

    # rediscover with the setting in the config
    site.delete_file(f"var/check_mk/autochecks/{host_name}.mk")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
    entries = _AutochecksSerializer().deserialize(
        site.read_file(f"var/check_mk/autochecks/{host_name}.mk").encode("utf-8")
    )
    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_1":
            assert entry.item == "Parameters({'default': 42, 'levels': (1, 2)})"
            break
    else:
        raise AssertionError('"test_check_1" not discovered')


def test_test_check_1_all_rule(request: pytest.FixtureRequest, site: Site) -> None:
    host_name = "disco-params-test-host"

    create_linux_test_host(request, site, host_name)
    site.write_file("var/check_mk/agent_output/disco-params-test-host", "<<<test_check_2>>>\n1 2\n")

    test_check_dir = "local/lib/python3/cmk/plugins/collection/agent_based"
    test_check_path = f"{test_check_dir}/test_check_2.py"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_2.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_2.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.makedirs(test_check_dir)
    site.write_file(
        test_check_path,
        """
import pprint

from cmk.agent_based.v2 import CheckPlugin, Service, RuleSetType


def discover(params, section):
    yield Service(item=pprint.pformat(params))


def check(item, section):
    return
    yield


check_plugin_test_check_2 = CheckPlugin(
    name="test_check_2",
    discovery_function=discover,
    discovery_ruleset_name="discover_test_check_2",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"default": 42},
    check_function=check,
    service_name="Foo %s",
)
""",
    )

    site.activate_changes_and_wait_for_core_reload()
    _restart_automation_helpers_and_wait_until_reachable(site)

    site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)

    # Verify that the discovery worked as expected
    entries = _AutochecksSerializer().deserialize(
        site.read_file(f"var/check_mk/autochecks/{host_name}.mk").encode("utf-8")
    )

    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_2":
            assert entry.item == "[Parameters({'default': 42})]"
            break
    else:
        raise AssertionError('"test_check_2" not discovered')

    # And now overwrite the setting in the config
    site.write_file(
        "etc/check_mk/conf.d/test_check_2.mk",
        "discover_test_check_2 = [{'value': {'levels': (1, 2)}, 'condition': {}}]\n",
    )

    # rediscover with the setting in the config
    site.delete_file(f"var/check_mk/autochecks/{host_name}.mk")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
    entries = _AutochecksSerializer().deserialize(
        site.read_file(f"var/check_mk/autochecks/{host_name}.mk").encode("utf-8")
    )
    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_2":
            assert entry.item == ("[Parameters({'levels': (1, 2)}), Parameters({'default': 42})]")
            break
    else:
        raise AssertionError('"test_check_2" not discovered')


def _restart_automation_helpers_and_wait_until_reachable(site: Site) -> None:
    def automation_helper_socket_reachable() -> bool:
        try:
            site.python_helper("_helper_connect_to_automation_helper_socket.py").check_output()
        except subprocess.CalledProcessError:
            return False
        return True

    site.omd("restart", "automation-helper")
    wait_until(
        automation_helper_socket_reachable,
        timeout=10,
        interval=0.25,
    )
