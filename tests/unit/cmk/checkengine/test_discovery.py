#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.labels import HostLabel

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import (
    _filters,
    analyse_services,
    AutocheckEntry,
    DiscoveryMode,
    QualifiedDiscovery,
)
from cmk.checkengine.discovery._utils import DiscoveredItem


def _service(plugin_name: str, item: str) -> AutocheckEntry:
    return AutocheckEntry(CheckPluginName(plugin_name), item, {}, {})


def test_discover_keep_vanished_and_remember() -> None:
    result = analyse_services(
        existing_services=[_service("A", "1")],
        discovered_services=[_service("B", "1")],
        run_plugin_names=EVERYTHING,
        forget_existing=False,
        keep_vanished=True,
    )

    assert not result.vanished
    assert result.old == [_service("A", "1")]
    assert result.new == [_service("B", "1")]


def test_discover_drop_vanished_but_remember() -> None:
    result = analyse_services(
        existing_services=[_service("A", "1")],
        discovered_services=[_service("B", "1")],
        run_plugin_names=EVERYTHING,
        forget_existing=False,
        keep_vanished=False,
    )

    assert result.vanished == [_service("A", "1")]
    assert not result.old
    assert result.new == [_service("B", "1")]


def test_discover_forget_everything_but_keep_it() -> None:
    result = analyse_services(
        existing_services=[_service("A", "1")],
        discovered_services=[_service("B", "1")],
        run_plugin_names=EVERYTHING,
        forget_existing=True,
        keep_vanished=True,
    )
    assert not result.vanished
    assert not result.old
    assert result.new == result.present
    assert result.new == [_service("B", "1"), _service("A", "1")]


def test_discover_forget_everything_and_clear() -> None:  # a.k.a. "tabula rasa"
    result = analyse_services(
        existing_services=[_service("A", "1")],
        discovered_services=[_service("B", "1")],
        run_plugin_names=EVERYTHING,
        forget_existing=True,
        keep_vanished=False,
    )

    assert not result.vanished
    assert not result.old
    assert result.new == result.present
    assert result.new == [_service("B", "1")]


def test_discover_run_plugin_names() -> None:
    result = analyse_services(
        existing_services=[_service("A", "1"), _service("B", "1")],
        discovered_services=[_service("B", "2")],
        run_plugin_names={CheckPluginName("B")},
        forget_existing=False,
        keep_vanished=False,
    )

    assert result.vanished == [_service("B", "1")]
    assert result.old == [_service("A", "1")]
    assert result.new == [_service("B", "2")]


def test_discover_run_plugin_names_forget() -> None:
    # this combination does not really make sense, but this is what we'd expect to happen.
    result = analyse_services(
        existing_services=[_service("A", "1"), _service("B", "1")],
        discovered_services=[_service("B", "2")],
        run_plugin_names={CheckPluginName("B")},
        forget_existing=True,
        keep_vanished=False,
    )

    assert not result.vanished
    assert result.old == [_service("A", "1")]
    assert result.new == [_service("B", "2")]


class TestDiscoveryMode:
    @staticmethod
    def test_modes_wato() -> None:
        # these are special, in the sense that they might be contained in
        # users configs, so they must be created from 0-3.
        assert DiscoveryMode(0) is DiscoveryMode.NEW
        assert DiscoveryMode(1) is DiscoveryMode.REMOVE
        assert DiscoveryMode(2) is DiscoveryMode.FIXALL
        assert DiscoveryMode(3) is DiscoveryMode.REFRESH

    @staticmethod
    def test_modes_invalid() -> None:
        invalid = len(DiscoveryMode)
        assert DiscoveryMode(invalid) is DiscoveryMode.FALLBACK
        with pytest.raises(KeyError):
            _ = DiscoveryMode.from_str("UNKNOWN")

    @staticmethod
    def test_modes_automation() -> None:
        # these strings are used by (remote) automation calls, and must not be changed!
        assert DiscoveryMode.from_str("new") is DiscoveryMode.NEW
        assert DiscoveryMode.from_str("remove") is DiscoveryMode.REMOVE
        assert DiscoveryMode.from_str("fixall") is DiscoveryMode.FIXALL
        assert DiscoveryMode.from_str("refresh") is DiscoveryMode.REFRESH
        assert DiscoveryMode.from_str("only-host-labels") == DiscoveryMode.ONLY_HOST_LABELS


@dataclass(frozen=True)
class _Discoverable:
    name: str
    value: str = ""

    def id(self) -> str:
        return self.name

    def comparator(self) -> str:
        return self.value


def test_qualified_discovery() -> None:
    result = QualifiedDiscovery(
        preexisting=(_Discoverable("one"), _Discoverable("two")),
        current=(_Discoverable("two"), _Discoverable("three")),
    )

    assert result.vanished == [_Discoverable("one")]
    assert result.old == [_Discoverable("two")]
    assert result.new == [_Discoverable("three")]
    assert result.present == [_Discoverable("two"), _Discoverable("three")]

    assert list(result.chain_with_transition()) == [
        ("vanished", DiscoveredItem(previous=_Discoverable(name="one", value=""), new=None)),
        (
            "unchanged",
            DiscoveredItem(
                previous=_Discoverable(name="two", value=""),
                new=_Discoverable(name="two", value=""),
            ),
        ),
        ("new", DiscoveredItem(previous=None, new=_Discoverable(name="three", value=""))),
    ]


def test_qualified_discovery_keeps_old() -> None:
    # This behaviour is debatable; but this is the way it is, so test it.
    # e.g.: same service, changed parameters
    result = QualifiedDiscovery(
        preexisting=[_Discoverable("name", "old value")],
        current=[_Discoverable("name", "new value")],
    )

    assert not result.vanished
    assert result.old == [_Discoverable("name", "old value")]
    assert not result.new
    assert result.present == [_Discoverable("name", "old value")]


def test_qualified_discovery_replaced() -> None:
    # Note: this does not keep the old value, but the new one.
    result = QualifiedDiscovery(
        preexisting=[HostLabel("a", "1"), HostLabel("b", "1")],
        current=[HostLabel("a", "1"), HostLabel("b", "2")],
    )

    assert result.vanished == [HostLabel("b", "1")]
    assert result.old == [HostLabel("a", "1")]
    assert result.new == [HostLabel("b", "2")]
    assert result.present == [HostLabel("a", "1"), HostLabel("b", "2")]


@pytest.mark.parametrize(
    "parameters_rediscovery",
    [
        {},
        {
            "service_whitelist": [],
        },
        {
            "service_blacklist": [],
        },
        {
            "service_whitelist": [],
            "service_blacklist": [],
        },
        {
            "vanished_service_whitelist": [],
        },
        {
            "vanished_service_blacklist": [],
        },
        {
            "vanished_service_whitelist": [],
            "vanished_service_blacklist": [],
        },
    ],
)
def test__get_service_filter_func_no_lists(
    parameters_rediscovery: _filters.RediscoveryParameters,
) -> None:
    service_filters = _filters.ServiceFilters.from_settings(parameters_rediscovery)
    assert service_filters.new is _filters._accept_all_services
    assert service_filters.vanished is _filters._accept_all_services


@pytest.mark.parametrize(
    "whitelist, result",
    [
        (["^Test"], True),
        (["^test"], False),
        ([".*Description"], True),
        ([".*Descript$"], False),
    ],
)
def test__get_service_filter_func_same_lists(
    monkeypatch: pytest.MonkeyPatch, whitelist: Sequence[str], result: bool
) -> None:
    service_filters = _filters.ServiceFilters.from_settings({"service_whitelist": whitelist})
    assert service_filters.new is not None
    assert service_filters.new("Test Description") is result

    service_filters_inv = _filters.ServiceFilters.from_settings({"service_blacklist": whitelist})
    assert service_filters_inv.new is not None
    assert service_filters_inv.new("Test Description") is not result

    service_filters_both = _filters.ServiceFilters.from_settings(
        {
            "service_whitelist": whitelist,
            "service_blacklist": whitelist,
        }
    )
    assert service_filters_both.new is not None
    assert service_filters_both.new("Test Description") is False


@pytest.mark.parametrize(
    "parameters_rediscovery, result",
    [
        (
            {
                # Matches
                "service_whitelist": ["^Test"],
                # Does not match
                "service_blacklist": [".*Descript$"],
            },
            True,
        ),
        (
            {
                # Matches
                "service_whitelist": ["^Test"],
                # Matches
                "service_blacklist": [".*Description$"],
            },
            False,
        ),
        (
            {
                # Does not match
                "service_whitelist": ["^test"],
                # Matches
                "service_blacklist": [".*Description$"],
            },
            False,
        ),
        (
            {
                # Does not match
                "service_whitelist": ["^test"],
                # Does not match
                "service_blacklist": [".*Descript$"],
            },
            False,
        ),
    ],
)
def test__get_service_filter_func(
    parameters_rediscovery: _filters.RediscoveryParameters,
    result: bool,
) -> None:
    service_filters = _filters.ServiceFilters.from_settings(parameters_rediscovery)
    assert service_filters.new is not None
    assert service_filters.new("Test Description") is result


@pytest.mark.parametrize(
    "parameters, new_whitelist, new_blacklist, vanished_whitelist, vanished_blacklist, changed_labels_whitelist, changed_labels_blacklist, changed_params_whitelist, changed_params_blacklist",
    [
        ({}, None, None, None, None, None, None, None, None),
        ({}, None, None, None, None, None, None, None, None),
        (
            {
                "service_whitelist": ["white"],
            },
            ["white"],
            None,
            ["white"],
            None,
            ["white"],
            None,
            ["white"],
            None,
        ),
        (
            {
                "service_blacklist": ["black"],
            },
            None,
            ["black"],
            None,
            ["black"],
            None,
            ["black"],
            None,
            ["black"],
        ),
        (
            {
                "service_whitelist": ["white"],
                "service_blacklist": ["black"],
            },
            ["white"],
            ["black"],
            ["white"],
            ["black"],
            ["white"],
            ["black"],
            ["white"],
            ["black"],
        ),
        (
            {
                "service_filters": ("combined", {}),
            },
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "combined",
                    {
                        "service_whitelist": ["white"],
                    },
                ),
            },
            ["white"],
            None,
            ["white"],
            None,
            ["white"],
            None,
            ["white"],
            None,
        ),
        (
            {
                "service_filters": (
                    "combined",
                    {
                        "service_blacklist": ["black"],
                    },
                ),
            },
            None,
            ["black"],
            None,
            ["black"],
            None,
            ["black"],
            None,
            ["black"],
        ),
        (
            {
                "service_filters": (
                    "combined",
                    {
                        "service_whitelist": ["white"],
                        "service_blacklist": ["black"],
                    },
                ),
            },
            ["white"],
            ["black"],
            ["white"],
            ["black"],
            ["white"],
            ["black"],
            ["white"],
            ["black"],
        ),
        (
            {
                "service_filters": ("dedicated", {}),
            },
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white"],
                    },
                ),
            },
            ["white"],
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black"],
                    },
                ),
            },
            None,
            ["black"],
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white"],
                        "service_blacklist": ["black"],
                    },
                ),
            },
            ["white"],
            ["black"],
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "vanished_service_whitelist": ["white"],
                    },
                ),
            },
            None,
            None,
            ["white"],
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "vanished_service_blacklist": ["black"],
                    },
                ),
            },
            None,
            None,
            None,
            ["black"],
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "vanished_service_whitelist": ["white"],
                        "vanished_service_blacklist": ["black"],
                        "changed_service_labels_blacklist": ["black"],
                        "changed_service_labels_whitelist": ["white"],
                    },
                ),
            },
            None,
            None,
            ["white"],
            ["black"],
            ["white"],
            ["black"],
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                        "changed_service_labels_whitelist": ["white_changed"],
                        "changed_service_params_whitelist": ["white_changed"],
                    },
                ),
            },
            ["white_new"],
            None,
            ["white_vanished"],
            None,
            ["white_changed"],
            None,
            ["white_changed"],
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            ["white_new"],
            None,
            None,
            ["black_vanished"],
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                    },
                ),
            },
            None,
            ["black_new"],
            ["white_vanished"],
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black_new"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            None,
            ["black_new"],
            None,
            ["black_vanished"],
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                    },
                ),
            },
            ["white_new"],
            ["black_new"],
            ["white_vanished"],
            None,
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "service_blacklist": ["black_new"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            ["white_new"],
            ["black_new"],
            None,
            ["black_vanished"],
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                        "vanished_service_blacklist": ["black_vanished"],
                        "changed_service_labels_blacklist": ["black_changed"],
                        "changed_service_labels_whitelist": ["white_changed"],
                        "changed_service_params_blacklist": ["black_changed"],
                        "changed_service_params_whitelist": ["white_changed"],
                    },
                ),
            },
            ["white_new"],
            ["black_new"],
            ["white_vanished"],
            ["black_vanished"],
            ["white_changed"],
            ["black_changed"],
            ["white_changed"],
            ["black_changed"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            ["white_new"],
            None,
            ["white_vanished"],
            ["black_vanished"],
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            None,
            ["black_new"],
            ["white_vanished"],
            ["black_vanished"],
            None,
            None,
            None,
            None,
        ),
    ],
)
def test__get_service_filters_lists(
    parameters,
    new_whitelist,
    new_blacklist,
    vanished_whitelist,
    vanished_blacklist,
    changed_labels_whitelist,
    changed_labels_blacklist,
    changed_params_whitelist,
    changed_params_blacklist,
):
    service_filter_lists = _filters._get_service_filter_lists(parameters)
    assert service_filter_lists.new_whitelist == new_whitelist
    assert service_filter_lists.new_blacklist == new_blacklist
    assert service_filter_lists.vanished_whitelist == vanished_whitelist
    assert service_filter_lists.vanished_blacklist == vanished_blacklist
    assert service_filter_lists.changed_labels_whitelist == changed_labels_whitelist
    assert service_filter_lists.changed_labels_blacklist == changed_labels_blacklist
    assert service_filter_lists.changed_params_whitelist == changed_params_whitelist
    assert service_filter_lists.changed_params_blacklist == changed_params_blacklist

    service_filters = _filters.ServiceFilters.from_settings(parameters)
    assert service_filters.new is not None
    assert service_filters.vanished is not None
