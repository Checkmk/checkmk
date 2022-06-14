#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import CheckPluginName, EVERYTHING

from cmk.base.agent_based.discovery._discovered_services import _analyse_discovered_services
from cmk.base.autochecks import AutocheckEntry


def _service(plugin_name: str, item: str) -> AutocheckEntry:
    return AutocheckEntry(CheckPluginName(plugin_name), item, {}, {})


def test_discover_keep_vanished_and_remember() -> None:

    result = _analyse_discovered_services(
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

    result = _analyse_discovered_services(
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

    result = _analyse_discovered_services(
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

    result = _analyse_discovered_services(
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

    result = _analyse_discovered_services(
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
    result = _analyse_discovered_services(
        existing_services=[_service("A", "1"), _service("B", "1")],
        discovered_services=[_service("B", "2")],
        run_plugin_names={CheckPluginName("B")},
        forget_existing=True,
        keep_vanished=False,
    )

    assert not result.vanished
    assert result.old == [_service("A", "1")]
    assert result.new == [_service("B", "2")]
