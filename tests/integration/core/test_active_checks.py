#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import collections
import pytest  # type: ignore[import]

from testlib.utils import api_str_type
from testlib.fixtures import web  # noqa: F401 # pylint: disable=unused-import

DefaultConfig = collections.namedtuple("DefaultConfig", ["core"])

logger = logging.getLogger(__name__)


@pytest.fixture(name="test_cfg", scope="module", params=["nagios", "cmc"])
def test_cfg_fixture(request, web, site):  # noqa: F811 # pylint: disable=redefined-outer-name
    config = DefaultConfig(core=request.param)
    site.set_config("CORE", config.core, with_restart=True)

    print("Applying default config")
    web.add_host("test-host", attributes={
        "ipaddress": "127.0.0.1",
        "tag_agent": "no-agent",
    })

    web.activate_changes()
    yield config

    #
    # Cleanup code
    #
    print("Cleaning up test config")

    web.delete_host("test-host")


def test_active_check_execution(test_cfg, site, web):  # noqa: F811 # pylint: disable=redefined-outer-name
    try:
        # TODO: Remove bytestr marker once the GUI uses Python 3
        web.set_ruleset(
            api_str_type("custom_checks"),
            {
                api_str_type("ruleset"): {
                    # Main folder
                    api_str_type(""): [{
                        api_str_type("value"): {
                            api_str_type('service_description'): u'\xc4ctive-Check',
                            api_str_type('command_line'): api_str_type('echo "123"')
                        },
                        api_str_type("condition"): {},
                        api_str_type("options"): {},
                    },],
                }
            })
        web.activate_changes()

        site.schedule_check("test-host", u'\xc4ctive-Check', 0)

        result = site.live.query_row(
            u"GET services\nColumns: host_name description state plugin_output has_been_checked\nFilter: host_name = test-host\nFilter: description = \xc4ctive-Check"
        )
        print("Result: %r" % result)
        assert result[4] == 1
        assert result[0] == "test-host"
        assert result[1] == u'\xc4ctive-Check'
        assert result[2] == 0
        assert result[3] == "123"
    finally:
        # TODO: Remove bytestr marker once the GUI uses Python 3
        web.set_ruleset(
            api_str_type("custom_checks"),
            {
                api_str_type("ruleset"): {
                    api_str_type(""): [],  # -> folder
                }
            })
        web.activate_changes()


def test_active_check_macros(test_cfg, site, web):  # noqa: F811 # pylint: disable=redefined-outer-name
    macros = {
        "$HOSTADDRESS$": "127.0.0.1",
        "$HOSTNAME$": "test-host",
        "$_HOSTTAGS$": " ".join(
            sorted([
                "/wato/", "auto-piggyback", "ip-v4", "ip-v4-only", "lan", "no-agent", "no-snmp",
                "ping", "prod",
                "site:%s" % site.id
            ])),
        "$_HOSTADDRESS_4$": "127.0.0.1",
        "$_HOSTADDRESS_6$": "",
        "$_HOSTADDRESS_FAMILY$": "4",
        "$USER1$": "/omd/sites/%s/lib/nagios/plugins" % site.id,
        "$USER2$": "/omd/sites/%s/local/lib/nagios/plugins" % site.id,
        "$USER3$": site.id,
        "$USER4$": site.root,
    }

    def descr(var):
        return "Macro %s" % var.strip("$")

    ruleset = []
    for var, value in macros.items():
        ruleset.append({
            "value": {
                'service_description': descr(var),
                # TODO: Remove this once the GUI uses Python 3
                'command_line': api_str_type('echo "Output: %s"' % var),
            },
            "condition": {},
        })

    try:
        web.set_ruleset(
            "custom_checks",
            {
                "ruleset": {
                    # Main folder
                    "": ruleset,
                }
            })
        web.activate_changes()

        for var, value in macros.items():
            description = descr(var)
            logger.info(description)
            site.schedule_check("test-host", description, 0)

            logger.info("Get service row")
            row = site.live.query_row(
                "GET services\n"
                "Columns: host_name description state plugin_output has_been_checked\n"
                "Filter: host_name = test-host\n"
                "Filter: description = %s\n" % description)

            logger.info(row)
            name, description, state, plugin_output, has_been_checked = row

            assert name == "test-host"
            assert has_been_checked == 1
            assert state == 0

            expected_output = "Output: %s" % value
            # TODO: Cleanup difference between nagios/cmc
            if test_cfg.core == "nagios":
                expected_output = expected_output.strip()
                if var == "$_HOSTTAGS$":
                    splitted_output = plugin_output.split(" ")
                    plugin_output = splitted_output[0] + " " + " ".join(sorted(splitted_output[1:]))

            assert expected_output == plugin_output, \
                "Macro %s has wrong value (%r instead of %r)" % (var, plugin_output, expected_output)

    finally:
        web.set_ruleset(
            "custom_checks",
            {
                "ruleset": {
                    "": [],  # -> folder
                }
            })
        web.activate_changes()
