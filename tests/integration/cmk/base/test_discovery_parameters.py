#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib.fixtures import web  # noqa: F401 # pylint: disable=unused-import

import cmk.base.config as config
import cmk.base.check_api as check_api
import cmk.base.autochecks as autochecks


@pytest.fixture(name="test_cfg", scope="module")
def test_cfg_fixture(web, site):  # noqa: F811 # pylint: disable=redefined-outer-name
    print("Applying default config")
    web.add_host("modes-test-host", attributes={
        "ipaddress": "127.0.0.1",
    })

    site.write_file(
        "etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['modes-test-host']))\n"
    )

    site.makedirs("var/check_mk/agent_output/")
    web.activate_changes()

    yield None

    #
    # Cleanup code
    #
    print("Cleaning up test config")
    web.delete_host("modes-test-host")


def test_test_check_1_merged_rule(request, test_cfg, site, web):  # noqa: F811 # pylint: disable=redefined-outer-name

    test_check_path = "local/lib/check_mk/base/plugins/agent_based/test_check_1.py"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_1.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_1.mk")

        if site.file_exists("var/check_mk/autochecks/modes-test-host.mk"):
            site.delete_file("var/check_mk/autochecks/modes-test-host.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_file(
        test_check_path, """
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
    discovery_ruleset_type="merged",
    discovery_default_parameters={"default": 42},
    check_function=check,
    service_name="Foo %s",
)
""")

    site.write_file("var/check_mk/agent_output/modes-test-host", "<<<test_check_1>>>\n1 2\n")

    config.load_all_agent_based_plugins(check_api.get_check_api_context)
    config.load(with_conf_d=False)

    web.discover_services("modes-test-host")

    # Verify that the discovery worked as expected
    services = autochecks.parse_autochecks_file("modes-test-host", config.service_description)
    for service in services:
        if str(service.check_plugin_name) == "test_check_1":
            assert service.item == "Parameters({'default': 42})"
            break
    else:
        assert False, '"test_check_1" not discovered'

    # And now overwrite the setting in the config
    site.write_file("etc/check_mk/conf.d/test_check_1.mk",
                    "discover_test_check_1 = [{'value': {'levels': (1, 2)}, 'condition': {}}]\n")

    # rediscover with the setting in the config
    site.delete_file("var/check_mk/autochecks/modes-test-host.mk")
    web.discover_services("modes-test-host")
    services = autochecks.parse_autochecks_file("modes-test-host", config.service_description)
    for service in services:
        if str(service.check_plugin_name) == "test_check_1":
            assert service.item == "Parameters({'default': 42, 'levels': (1, 2)})"
            break
    else:
        assert False, '"test_check_1" not discovered'


def test_test_check_1_all_rule(request, test_cfg, site, web):  # noqa: F811 # pylint: disable=redefined-outer-name

    test_check_path = "local/lib/check_mk/base/plugins/agent_based/test_check_2.py"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_2.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_2.mk")

        if site.file_exists("var/check_mk/autochecks/modes-test-host.mk"):
            site.delete_file("var/check_mk/autochecks/modes-test-host.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_file(
        test_check_path, """
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
    discovery_ruleset_type="all",
    discovery_default_parameters={"default": 42},
    check_function=check,
    service_name="Foo %s",
)
""")

    site.write_file("var/check_mk/agent_output/modes-test-host", "<<<test_check_2>>>\n1 2\n")

    config.load_all_agent_based_plugins(check_api.get_check_api_context)
    config.load(with_conf_d=False)

    web.discover_services("modes-test-host")

    # Verify that the discovery worked as expected
    services = autochecks.parse_autochecks_file("modes-test-host", config.service_description)
    for service in services:
        if str(service.check_plugin_name) == "test_check_2":
            assert service.item == "[Parameters({'default': 42})]"
            break
    else:
        assert False, '"test_check_2" not discovered'

    # And now overwrite the setting in the config
    site.write_file("etc/check_mk/conf.d/test_check_2.mk",
                    "discover_test_check_2 = [{'value': {'levels': (1, 2)}, 'condition': {}}]\n")

    # rediscover with the setting in the config
    site.delete_file("var/check_mk/autochecks/modes-test-host.mk")
    web.discover_services("modes-test-host")
    services = autochecks.parse_autochecks_file("modes-test-host", config.service_description)
    for service in services:
        if str(service.check_plugin_name) == "test_check_2":
            assert service.item == ("[Parameters({'levels': (1, 2)}),"
                                    " Parameters({'default': 42})]")
            break
    else:
        assert False, '"test_check_2" not discovered'
