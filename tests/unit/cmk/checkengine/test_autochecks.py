#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths

from cmk.checkengine.discovery import AutocheckServiceWithNodes, AutochecksStore
from cmk.checkengine.discovery._autochecks import _AutochecksSerializer as AutochecksSerializer
from cmk.checkengine.discovery._autochecks import _consolidate_autochecks_of_real_hosts
from cmk.checkengine.discovery._utils import DiscoveredItem
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName


@pytest.fixture(autouse=True)
def autochecks_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cmk.utils.paths, "autochecks_dir", tmp_path)


class TestAutochecksSerializer:
    def test_empty(self) -> None:
        serial = b"[\n]\n"
        obj: list[AutocheckEntry] = []
        assert AutochecksSerializer.serialize(obj) == serial
        assert AutochecksSerializer.deserialize(serial) == obj

    def test_with_item(self) -> None:
        serial = (
            b"[\n  {'check_plugin_name': 'norris', 'item': 'abc',"
            b" 'parameters': {}, 'service_labels': {}},\n]\n"
        )
        obj = [AutocheckEntry(CheckPluginName("norris"), "abc", {}, {})]
        assert AutochecksSerializer.serialize(obj) == serial
        assert AutochecksSerializer.deserialize(serial) == obj

    def test_without_item(self) -> None:
        serial = (
            b"[\n  {'check_plugin_name': 'norris', 'item': None,"
            b" 'parameters': {}, 'service_labels': {}},\n]\n"
        )
        obj = [AutocheckEntry(CheckPluginName("norris"), None, {}, {})]
        assert AutochecksSerializer.serialize(obj) == serial
        assert AutochecksSerializer.deserialize(serial) == obj


def _entries() -> Sequence[AutocheckEntry]:
    return [AutocheckEntry(CheckPluginName("norris"), "abc", {}, {})]


class TestAutochecksStore:
    def test_clear(self) -> None:
        store = AutochecksStore(HostName("herbert"))
        store.write(_entries())
        assert store.read()
        store.clear()
        assert not store.read()

    def test_write_read(self) -> None:
        store = AutochecksStore(HostName("herbert"))
        store.write(_entries())
        assert store.read() == _entries()


@pytest.mark.usefixtures("agent_based_plugins")
@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        # Dict: Regular processing
        (
            """[
  {'check_plugin_name': 'df', 'item': u'/', 'parameters': {}, 'service_labels': {}},
]""",
            [
                AutocheckEntry(
                    check_plugin_name=CheckPluginName("df"),
                    item="/",
                    parameters={},
                    service_labels={},
                ),
            ],
        ),
    ],
)
def test_manager_get_autochecks_of(
    autochecks_content: str,
    expected_result: Sequence[AutocheckEntry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with (cmk.utils.paths.autochecks_dir / "host.mk").open("w", encoding="utf-8") as f:
        f.write(autochecks_content)

    ts = Scenario()
    ts.add_host(HostName("host"))
    config_cache = ts.apply(monkeypatch)

    manager = config_cache.autochecks_manager

    result = manager.get_autochecks(HostName("host"))
    assert result == expected_result


def _entry(name: str, params: dict[str, str] | None = None) -> AutocheckEntry:
    return AutocheckEntry(CheckPluginName(name), None, params or {}, {})


def test_consolidate_autochecks_of_real_hosts() -> None:
    new_services_with_nodes = [
        AutocheckServiceWithNodes(  # found on node and new
            DiscoveredItem(new=_entry("A"), previous=None),
            [HostName("node"), HostName("othernode")],
        ),
        AutocheckServiceWithNodes(  # not found, not present (i.e. unrelated)
            DiscoveredItem(previous=_entry("B"), new=_entry("B")),
            [HostName("othernode"), HostName("yetanothernode")],
        ),
        AutocheckServiceWithNodes(  # found and preexistting
            DiscoveredItem(new=_entry("C", {"params": "new"}), previous=None),
            [HostName("node"), HostName("node2")],
        ),
        AutocheckServiceWithNodes(  # not found but present
            DiscoveredItem(new=_entry("D"), previous=_entry("D")),
            [HostName("othernode"), HostName("yetanothernode")],
        ),
    ]
    preexisting_entries = [
        _entry("C", {"params": "old"}),  # still there
        _entry("D"),  # no longer found on the node
        _entry("E"),  # not found at all
    ]

    # the dict is just b/c it's easier to test against.
    consolidated = _consolidate_autochecks_of_real_hosts(
        HostName("node"),
        new_services_with_nodes,
        preexisting_entries,
    )

    # for easier test access:
    by_plugin = {str(e.check_plugin_name): e for e in consolidated}

    # these are entries we expect (Note: this is status quo. Not sure why we keep service D):
    assert len(consolidated) == 3
    assert set(by_plugin) == {"A", "C", "D"}
    assert by_plugin["C"].parameters == {"params": "new"}
