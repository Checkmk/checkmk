#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import pytest  # type: ignore[import]

from cmk.ec.main import HostConfig


@pytest.fixture(name="host_config")
def fixture_host_config():
    return HostConfig(logging.getLogger("cmk.mkeventd.EventServer"))


def _heute_config():
    return {
        'name': 'heute',
        'alias': 'heute alias',
        'address': '127.0.0.1',
        'custom_variables': {
            "FILENAME": "/wato/hosts.mk",
            "ADDRESS_FAMILY": "4",
            "ADDRESS_4": "127.0.0.1",
            "ADDRESS_6": "",
            "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
        },
        'contacts': [],
        'contact_groups': ['all'],
    }


def _example_com_config():
    return {
        'name': 'example.com',
        'alias': 'example.com alias',
        'address': 'server.example.com',
        'custom_variables': {
            "FILENAME": "/wato/hosts.mk",
            "ADDRESS_FAMILY": "4",
            "ADDRESS_4": "127.0.0.1",
            "ADDRESS_6": "",
            "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
        },
        'contacts': [],
        'contact_groups': ['all'],
    }


def _test_table():
    return [
        _heute_config(),
        _example_com_config(),
    ]


@pytest.fixture(name="live")
def fixture_livestatus(mock_livestatus):
    mock_livestatus.add_table('hosts', _test_table())
    return mock_livestatus


# TODO: It is beyond the scope of this test to verify the livestatus queries which are made, but the
# livestatus mocker requires to define all expected queries at the moment. We'll do so for now.
def test_host_config_get_config_for_host_by_name(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_config_for_host("heute", {}) == _heute_config()


# TODO: It is beyond the scope of this test to verify the livestatus queries which are made, but the
# livestatus mocker requires to define all expected queries at the moment. We'll do so for now.
def test_host_config_get_config_for_host_by_fuzzy_name_not_possible(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_config_for_host("HEUTE", {}) == {}


# TODO: It is beyond the scope of this test to verify the livestatus queries which are made, but the
# livestatus mocker requires to define all expected queries at the moment. We'll do so for now.
def test_host_config_get_config_for_host_by_address_not_possible(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_config_for_host("127.0.0.1", {}) == {}


def test_host_config_get_config_for_host_is_cached(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_config_for_host("heute", {}) == _heute_config()

        live.expect_query("GET status\n" "Columns: program_start")
        assert host_config.get_config_for_host("heute", {}) == _heute_config()


# TODO: It is beyond the scope of this test to verify the livestatus queries which are made, but the
# livestatus mocker requires to define all expected queries at the moment. We'll do so for now.
def test_host_config_get_canonical_name_by_name(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_canonical_name("heute") == "heute"

        live.expect_query("GET status\n" "Columns: program_start")
        assert host_config.get_canonical_name("HEUTE") == "heute"


# TODO: It is beyond the scope of this test to verify the livestatus queries which are made, but the
# livestatus mocker requires to define all expected queries at the moment. We'll do so for now.
def test_host_config_get_canonical_name_by_address(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_canonical_name("127.0.0.1") == "heute"

        live.expect_query("GET status\n" "Columns: program_start")
        assert host_config.get_canonical_name("server.example.com") == "example.com"

        live.expect_query("GET status\n" "Columns: program_start")
        assert host_config.get_canonical_name("SERVER.example.com") == "example.com"


# TODO: It is beyond the scope of this test to verify the livestatus queries which are made, but the
# livestatus mocker requires to define all expected queries at the moment. We'll do so for now.
def test_host_config_get_canonical_name_for_not_existing_host(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_canonical_name("not-matching") == ""


def test_host_config_get_canonical_name_is_cached(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_canonical_name("heute alias") == "heute"

        live.expect_query("GET status\n" "Columns: program_start")
        assert host_config.get_canonical_name("127.0.0.1") == "heute"


def test_host_config_get_canonical_name_is_cached_updated(host_config, live):
    with live(expect_status_query=False):
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_canonical_name("heute alias") == "heute"

        # Update the config to simulate a config change
        live._tables["hosts"][0]["alias"] = "new alias"
        live._tables["status"][0]["program_start"] = live._tables["status"][0]["program_start"] + 10

        # Original alias is not matching anymore, cache is updated
        live.expect_query("GET status\n" "Columns: program_start")
        live.expect_query("GET hosts\n"
                          "Columns: name alias address custom_variables contacts contact_groups")
        assert host_config.get_canonical_name("heute alias") == ""

        live.expect_query("GET status\n" "Columns: program_start")
        assert host_config.get_canonical_name("new alias") == "heute"
