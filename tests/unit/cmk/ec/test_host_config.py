#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.ec.core_queries import HostInfo
from cmk.ec.host_config import HostConfig


@pytest.fixture(name="host_config")
def fixture_host_config() -> HostConfig:
    return HostConfig(logging.getLogger("cmk.mkeventd.EventServer"))


def _heute_config() -> dict[str, object]:
    return {
        "name": "heute",
        "alias": "heute alias",
        "address": "127.0.0.1",
        "custom_variables": {
            "FILENAME": "/wato/hosts.mk",
            "ADDRESS_FAMILY": "4",
            "ADDRESS_4": "127.0.0.1",
            "ADDRESS_6": "",
            "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
        },
        "contacts": [],
        "contact_groups": ["all"],
        "groups": ["custom-group"],
    }


def _example_com_config() -> dict[str, object]:
    return {
        "name": "example.com",
        "alias": "example.com alias",
        "address": "server.example.com",
        "custom_variables": {
            "FILENAME": "/wato/hosts.mk",
            "ADDRESS_FAMILY": "4",
            "ADDRESS_4": "127.0.0.1",
            "ADDRESS_6": "",
            "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
        },
        "contacts": [],
        "contact_groups": ["all"],
        "groups": [],
    }


def _test_table() -> list[dict[str, object]]:
    return [
        _heute_config(),
        _example_com_config(),
    ]


@pytest.fixture(name="live")
def fixture_livestatus(
    patch_omd_site: None, mock_livestatus: MockLiveStatusConnection
) -> MockLiveStatusConnection:
    mock_livestatus.set_sites(["local"])
    mock_livestatus.add_table("hosts", _test_table())
    return mock_livestatus


@pytest.mark.parametrize(
    "hostname_str, result",
    [
        (
            "heute",
            HostInfo(
                name=HostName("heute"),
                alias="heute alias",
                address=HostAddress("127.0.0.1"),
                custom_variables={
                    "FILENAME": "/wato/hosts.mk",
                    "ADDRESS_FAMILY": "4",
                    "ADDRESS_4": "127.0.0.1",
                    "ADDRESS_6": "",
                    "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
                },
                contacts=set(),
                contact_groups={"all"},
                host_groups={"custom-group"},
            ),
        ),
        ("HEUTE", None),
        ("127.0.0.1", None),
    ],
)
def test_host_config(
    host_config: HostConfig,
    live: MockLiveStatusConnection,
    hostname_str: str,
    result: HostInfo | None,
) -> None:
    hostname = HostName(hostname_str)
    with live(expect_status_query=False):
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query(
            [
                "GET hosts",
                "Columns: name alias address custom_variables contacts contact_groups groups",
                "ColumnHeaders: on",
            ]
        )
        assert host_config.get_config_for_host(hostname) == result
        # Data is cached and not queried twice.
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        assert host_config.get_config_for_host(hostname) == result


@pytest.mark.parametrize(
    "search_term, result",
    [
        ("heute", HostName("heute")),
        ("HEUTE", HostName("heute")),
        ("127.0.0.1", HostName("heute")),
        ("server.example.com", HostName("example.com")),
        ("SERVER.example.com", HostName("example.com")),
        ("not-matching", None),
        ("heute alias", HostName("heute")),
    ],
)
def test_host_config_get_canonical_name(
    host_config: HostConfig,
    live: MockLiveStatusConnection,
    search_term: str,
    result: HostName | None,
) -> None:
    with live(expect_status_query=False):
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query(
            [
                "GET hosts",
                "Columns: name alias address custom_variables contacts contact_groups groups",
                "ColumnHeaders: on",
            ]
        )
        assert host_config.get_canonical_name(search_term) == result

        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        assert host_config.get_canonical_name(search_term) == result


def test_host_config_get_canonical_name_is_cached_updated(
    host_config: HostConfig, live: MockLiveStatusConnection
) -> None:
    with live(expect_status_query=False):
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query(
            [
                "GET hosts",
                "Columns: name alias address custom_variables contacts contact_groups groups",
                "ColumnHeaders: on",
            ]
        )
        assert host_config.get_canonical_name("heute alias") == HostName("heute")

        # Update the config to simulate a config change
        live.tables["hosts"]["local"][0]["alias"] = "new alias"
        live.tables["status"]["local"][0]["program_start"] = (
            live.tables["status"]["local"][0]["program_start"] + 10
        )

        # Original alias is not matching anymore, cache is updated
        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        live.expect_query(
            [
                "GET hosts",
                "Columns: name alias address custom_variables contacts contact_groups groups",
                "ColumnHeaders: on",
            ]
        )
        assert host_config.get_canonical_name("heute alias") is None

        live.expect_query(["GET status", "Columns: program_start", "ColumnHeaders: off"])
        assert host_config.get_canonical_name("new alias") == HostName("heute")
