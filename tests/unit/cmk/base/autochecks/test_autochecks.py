#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import pytest

from tests.testlib.base import Scenario

import cmk.utils.paths
from cmk.utils.type_defs import CheckPluginName, HostName, LegacyCheckParameters

import cmk.base.agent_based.discovery as discovery
import cmk.base.autochecks as autochecks
import cmk.base.config as config
from cmk.base.check_utils import AutocheckService
from cmk.base.discovered_labels import ServiceLabel


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
        autochecks.AutocheckEntry(CheckPluginName("df"), "/zzz", ["abc", "xyz"], {}),
        autochecks.AutocheckEntry(CheckPluginName("chrony"), None, {}, {}),
        autochecks.AutocheckEntry(
            CheckPluginName("lnx_if"), "2", {"speed": 10000000, "state": ["1"]}, {}
        ),
    ]
    autochecks.save_autochecks(HostName("host"), autocheck_entries)

    services = autochecks.parse_autochecks_services(
        HostName("host"),
        config.service_description,
    )

    assert [s.description for s in services] == [
        "fs_/zzz",
        "NTP Time",
        "Interface 2",
    ]


def test_remove_autochecks_file():
    autochecks_file = Path(cmk.utils.paths.autochecks_dir) / "host.mk"
    assert not autochecks_file.exists()

    autochecks.save_autochecks_services(HostName("host"), [])
    assert autochecks_file.exists()

    autochecks.remove_autochecks_file(HostName("host"))
    assert not autochecks_file.exists()


@pytest.mark.parametrize(
    "items,expected_content",
    [
        ([], "[\n]\n"),
        (
            [
                AutocheckService(
                    CheckPluginName("df"),
                    "/xyz",
                    "Filesystem /xyz",
                    None,
                    {"x": ServiceLabel("x", "y")},
                ),
                AutocheckService(
                    CheckPluginName("df"),
                    "/",
                    "Filesystem /",
                    {},
                    {"x": ServiceLabel("x", "y")},
                ),
                AutocheckService(
                    CheckPluginName("cpu_loads"),
                    None,
                    "CPU load",
                    {},
                    {"x": ServiceLabel("x", "y")},
                ),
            ],
            """[
  {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': {}, 'service_labels': {'x': 'y'}},
  {'check_plugin_name': 'df', 'item': '/', 'parameters': {}, 'service_labels': {'x': 'y'}},
  {'check_plugin_name': 'df', 'item': '/xyz', 'parameters': None, 'service_labels': {'x': 'y'}},
]\n""",
        ),
    ],
)
def test_save_autochecks_services(items: Sequence[AutocheckService], expected_content: str) -> None:
    autochecks.save_autochecks_services(HostName("host"), items)

    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("r", encoding="utf-8") as f:
        content = f.read()

    assert expected_content == content


def _service(name: str, params: Optional[Dict[str, str]] = None) -> AutocheckService:
    return AutocheckService(CheckPluginName(name), None, "", params or {})


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
    preexisting_services = [
        _service("C", {"params": "old"}),  # still there
        _service("D"),  # no longer found on the node
        _service("E"),  # not found at all
    ]

    consolidated = autochecks._consolidate_autochecks_of_real_hosts(
        HostName("node"),
        new_services_with_nodes,
        preexisting_services,
    )

    # these are service we expect:
    # Note: this is the status quo. I am not sure why we keep service D
    assert sorted(str(s.check_plugin_name) for s in consolidated) == ["A", "C", "D"]

    # and this one should have kept the old parameters
    service_c = [s for s in consolidated if str(s.check_plugin_name) == "C"][0]
    assert service_c.parameters == {"params": "old"}
