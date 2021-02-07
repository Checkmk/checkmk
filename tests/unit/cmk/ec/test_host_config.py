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
    mock_livestatus.set_sites(["local"])
    mock_livestatus.add_table('hosts', _test_table())
    return mock_livestatus


@pytest.mark.parametrize("search_term, result", [
    ("heute", _heute_config()),
    ("HEUTE", {}),
    ("127.0.0.1", {}),
])
def test_host_config(host_config, live, search_term, result):
    with live(expect_status_query=False):
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query([
            "GET hosts",
            "Columns: name alias address custom_variables contacts contact_groups",
            "ColumnHeaders: on",
        ])
        assert host_config.get_config_for_host(search_term, {}) == result
        # Data is cached and not queried twice.
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        assert host_config.get_config_for_host(search_term, {}) == result


@pytest.mark.parametrize("search_term, result", [
    ('heute', 'heute'),
    ('HEUTE', 'heute'),
    ('127.0.0.1', 'heute'),
    ('server.example.com', 'example.com'),
    ('SERVER.example.com', 'example.com'),
    ('not-matching', ''),
    ('heute alias', 'heute'),
])
def test_host_config_get_canonical_name(host_config, live, search_term, result):
    with live(expect_status_query=False):
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query([
            "GET hosts",
            "Columns: name alias address custom_variables contacts contact_groups",
            "ColumnHeaders: on",
        ])
        assert host_config.get_canonical_name(search_term) == result

        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        assert host_config.get_canonical_name(search_term) == result


def test_host_config_get_canonical_name_is_cached_updated(host_config, live):
    with live(expect_status_query=False):
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query([
            "GET hosts",
            "Columns: name alias address custom_variables contacts contact_groups",
            "ColumnHeaders: on",
        ])
        assert host_config.get_canonical_name("heute alias") == "heute"

        # Update the config to simulate a config change
        live.tables["hosts"]["local"][0]["alias"] = "new alias"
        live.tables["status"]["local"][0][
            "program_start"] = live.tables["status"]["local"][0]["program_start"] + 10

        # Original alias is not matching anymore, cache is updated
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query([
            "GET hosts",
            "Columns: name alias address custom_variables contacts contact_groups",
            "ColumnHeaders: on",
        ])
        assert host_config.get_canonical_name("heute alias") == ""

        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        assert host_config.get_canonical_name("new alias") == "heute"
