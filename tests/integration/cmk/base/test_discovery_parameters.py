#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import create_linux_test_host
from tests.testlib.site import Site

from cmk.utils.type_defs import HostName

import cmk.base.autochecks as autochecks


def test_test_check_1_merged_rule(request, site: Site, web):

    host_name = "disco-params-test-host"

    create_linux_test_host(request, site, host_name)
    site.write_text_file(f"var/check_mk/agent_output/{host_name}", "<<<test_check_1>>>\n1 2\n")

    test_check_path = "local/lib/check_mk/base/plugins/agent_based/test_check_1.py"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_1.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_1.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_text_file(
        test_check_path,
        """
import pprint

from .agent_based_api.v1 import register, Service


def discover(params, section):
    yield Service(item=pprint.pformat(params))


def check(item, section):
    return
    yield


register.check_plugin(
    name="test_check_1",
    discovery_function=discover,
    discovery_ruleset_name="discover_test_check_1",
    discovery_ruleset_type=register.RuleSetType.MERGED,
    discovery_default_parameters={"default": 42},
    check_function=check,
    service_name="Foo %s",
)
""",
    )

    site.activate_changes_and_wait_for_core_reload()

    web.discover_services(host_name)  # Replace with RestAPI call, see CMK-9249

    # Verify that the discovery worked as expected
    entries = autochecks.AutochecksStore(HostName(host_name)).read()
    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_1":
            assert entry.item == "Parameters({'default': 42})"
            break
    else:
        raise AssertionError('"test_check_1" not discovered')

    # And now overwrite the setting in the config
    site.write_text_file(
        "etc/check_mk/conf.d/test_check_1.mk",
        "discover_test_check_1 = [{'value': {'levels': (1, 2)}, 'condition': {}}]\n",
    )

    # rediscover with the setting in the config
    site.delete_file(f"var/check_mk/autochecks/{host_name}.mk")
    web.discover_services(host_name)  # Replace with RestAPI call, see CMK-9249
    entries = autochecks.AutochecksStore(HostName(host_name)).read()
    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_1":
            assert entry.item == "Parameters({'default': 42, 'levels': (1, 2)})"
            break
    else:
        raise AssertionError('"test_check_1" not discovered')


def test_test_check_1_all_rule(request, site: Site, web):

    host_name = "disco-params-test-host"

    create_linux_test_host(request, site, host_name)
    site.write_text_file(
        "var/check_mk/agent_output/disco-params-test-host", "<<<test_check_2>>>\n1 2\n"
    )

    test_check_path = "local/lib/check_mk/base/plugins/agent_based/test_check_2.py"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_2.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_2.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_text_file(
        test_check_path,
        """
import pprint

from .agent_based_api.v1 import register, Service


def discover(params, section):
    yield Service(item=pprint.pformat(params))


def check(item, section):
    return
    yield


register.check_plugin(
    name="test_check_2",
    discovery_function=discover,
    discovery_ruleset_name="discover_test_check_2",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"default": 42},
    check_function=check,
    service_name="Foo %s",
)
""",
    )

    site.activate_changes_and_wait_for_core_reload()

    web.discover_services(host_name)  # Replace with RestAPI call, see CMK-9249

    # Verify that the discovery worked as expected
    entries = autochecks.AutochecksStore(HostName(host_name)).read()

    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_2":
            assert entry.item == "[Parameters({'default': 42})]"
            break
    else:
        raise AssertionError('"test_check_2" not discovered')

    # And now overwrite the setting in the config
    site.write_text_file(
        "etc/check_mk/conf.d/test_check_2.mk",
        "discover_test_check_2 = [{'value': {'levels': (1, 2)}, 'condition': {}}]\n",
    )

    # rediscover with the setting in the config
    site.delete_file(f"var/check_mk/autochecks/{host_name}.mk")
    web.discover_services(host_name)  # Replace with RestAPI call, see CMK-9249
    entries = autochecks.AutochecksStore(HostName(host_name)).read()
    for entry in entries:
        if str(entry.check_plugin_name) == "test_check_2":
            assert entry.item == (
                "[Parameters({'levels': (1, 2)})," " Parameters({'default': 42})]"
            )
            break
    else:
        raise AssertionError('"test_check_2" not discovered')
