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
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import CheckPluginName, HostName

import cmk.base.autochecks as autochecks
import cmk.base.config as config
from cmk.base.check_utils import ConfiguredService

_COMPUTED_PARAMETERS_SENTINEL = TimespecificParameters(())


@pytest.fixture(autouse=True)
def autochecks_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", str(tmp_path))


@pytest.fixture()
def test_config(monkeypatch) -> config.ConfigCache:
    ts = Scenario()
    ts.add_host("host")
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
                ConfiguredService(
                    check_plugin_name=CheckPluginName("df"),
                    item="/",
                    description="df-/",  # we pass a simple callback, not the real one!
                    parameters=_COMPUTED_PARAMETERS_SENTINEL,
                    discovered_parameters={},
                    service_labels={},
                ),
            ],
        ),
    ],
)
def test_manager_get_autochecks_of(
    test_config: config.ConfigCache,
    autochecks_content: str,
    expected_result: Sequence[ConfiguredService],
) -> None:
    autochecks_file = Path(cmk.utils.paths.autochecks_dir, "host.mk")
    with autochecks_file.open("w", encoding="utf-8") as f:
        f.write(autochecks_content)

    manager = test_config._autochecks_manager

    result = manager.get_autochecks_of(
        HostName("host"),
        lambda *a: _COMPUTED_PARAMETERS_SENTINEL,
        lambda _host, check, item: f"{check}-{item}",
        lambda hostname, _desc: hostname,
    )
    assert result == expected_result
    # see that compute_check_parameters has been called:
    assert result[0].parameters is _COMPUTED_PARAMETERS_SENTINEL

    # Check that the ConfigCache method also returns the correct data
    assert test_config.get_autochecks_of(HostName("host")) == result


def _entry(name: str, params: Optional[Dict[str, str]] = None) -> autochecks.AutocheckEntry:
    return autochecks.AutocheckEntry(CheckPluginName(name), None, params or {}, {})


def test_consolidate_autochecks_of_real_hosts() -> None:

    new_services_with_nodes = [
        autochecks.AutocheckServiceWithNodes(  # found on node and new
            _entry("A"), [HostName("node"), HostName("othernode")]
        ),
        autochecks.AutocheckServiceWithNodes(  # not found, not present (i.e. unrelated)
            _entry("B"), [HostName("othernode"), HostName("yetanothernode")]
        ),
        autochecks.AutocheckServiceWithNodes(  # found and preexistting
            _entry("C", {"params": "new"}), [HostName("node"), HostName("node2")]
        ),
        autochecks.AutocheckServiceWithNodes(  # not found but present
            _entry("D"), [HostName("othernode"), HostName("yetanothernode")]
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
