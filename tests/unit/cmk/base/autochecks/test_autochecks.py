#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from pathlib import Path
from typing import Dict, Optional, Sequence

import pytest

from tests.testlib.base import Scenario

import cmk.utils.paths
from cmk.utils.type_defs import CheckPluginName, HostName

import cmk.base.agent_based.discovery as discovery
import cmk.base.autochecks as autochecks
import cmk.base.config as config
from cmk.base.check_utils import AutocheckService


@pytest.fixture(autouse=True)
def autochecks_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))


@pytest.fixture()
def test_config(monkeypatch) -> config.ConfigCache:
    ts = Scenario().add_host("host")
    return ts.apply(monkeypatch)


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        # Dict: Regular processing
        (
            """[
  {'check_plugin_name': 'df', 'item': u'/', 'parameters': {}, 'service_labels': {}},
]""",
            [
                discovery.Service(
                    CheckPluginName("df"),
                    "/",
                    "",
                    {
                        "inodes_levels": (10.0, 5.0),
                        "levels": (80.0, 90.0),
                        "levels_low": (50.0, 60.0),
                        "magic_normsize": 20,
                        "show_inodes": "onlow",
                        "show_levels": "onmagic",
                        "show_reserved": False,
                        "trend_perfdata": True,
                        "trend_range": 24,
                    },
                ),
            ],
        ),
    ],
)
def test_manager_get_autochecks_of(
    test_config: config.ConfigCache,
    autochecks_content: str,
    expected_result: Sequence[discovery.Service],
) -> None:
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:
        f.write(autochecks_content)

    manager = test_config._autochecks_manager

    result = manager.get_autochecks_of(
        HostName("host"),
        config.compute_check_parameters,
        config.service_description,
        lambda hostname, _desc: hostname,
    )
    assert result == expected_result

    # Check that the ConfigCache method also returns the correct data
    assert test_config.get_autochecks_of(HostName("host")) == result


@pytest.mark.usefixtures("fix_register")
def test_parse_autochecks_services(
    test_config: config.ConfigCache,
) -> None:
    autocheck_entries = [
        autochecks.AutocheckEntry(CheckPluginName("chrony"), None, {}, {}),
        autochecks.AutocheckEntry(CheckPluginName("df"), "/zzz", ["abc", "xyz"], {}),
        autochecks.AutocheckEntry(
            CheckPluginName("lnx_if"), "2", {"speed": 10000000, "state": ["1"]}, {}
        ),
    ]
    autochecks.AutochecksStore(HostName("host")).write(autocheck_entries)

    services = autochecks.parse_autochecks_services(
        HostName("host"),
        config.service_description,
    )

    assert [s.description for s in services] == [
        "NTP Time",
        "fs_/zzz",
        "Interface 2",
    ]


def _service(name: str, params: Optional[Dict[str, str]] = None) -> AutocheckService:
    return AutocheckService(CheckPluginName(name), None, "", params or {})


def _entry(name: str, params: Optional[Dict[str, str]] = None) -> autochecks.AutocheckEntry:
    return autochecks.AutocheckEntry(CheckPluginName(name), None, params or {}, {})


def test_consolidate_autochecks_of_real_hosts() -> None:

    new_services_with_nodes = [
        autochecks.AutocheckServiceWithNodes(  # found on node and new
            _service("A"), [HostName("node"), HostName("othernode")]
        ),
        autochecks.AutocheckServiceWithNodes(  # not found, not present (i.e. unrelated)
            _service("B"), [HostName("othernode"), HostName("yetanothernode")]
        ),
        autochecks.AutocheckServiceWithNodes(  # found and preexistting
            _service("C", {"params": "new"}), [HostName("node"), HostName("node2")]
        ),
        autochecks.AutocheckServiceWithNodes(  # not found but present
            _service("D"), [HostName("othernode"), HostName("yetanothernode")]
        ),
    ]
    preexisting_entries = [
        _entry("C", {"params": "old"}),  # still there
        _entry("D"),  # no longer found on the node
        _entry("E"),  # not found at all
    ]

    # the dict is just b/c it's easier to test against.
    consolidated = autochecks._consolidate_autochecks_of_real_hosts(
        HostName("node"),
        new_services_with_nodes,
        preexisting_entries,
    )

    # for easier test access:
    by_plugin = {str(e.check_plugin_name): e for e in consolidated}

    # these are entries we expect (Note: this is status quo. Not sure why we keep service D):
    assert len(consolidated) == 3
    assert set(by_plugin) == {"A", "C", "D"}
    # and this one should have kept the old parameters
    assert by_plugin["C"].parameters == {"params": "old"}
