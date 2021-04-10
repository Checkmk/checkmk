#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import CheckPluginName, EVERYTHING
from cmk.base.check_utils import Service

from cmk.base.agent_based.discovery._discovered_services import _analyse_discovered_services


def _service(plugin_name: str, item: str) -> Service:
    return Service(CheckPluginName(plugin_name), item, "", {})


def test_discover_only_new():

    result = _analyse_discovered_services(
        existing_services=[_service("A", "1")],
        discovered_services=[_service("B", "1")],
        run_plugin_names=EVERYTHING,
        only_new=True,
    )

    assert not result.vanished
    assert result.old == [_service("A", "1")]
    assert result.new == [_service("B", "1")]


def test_discover_not_only_new():

    result = _analyse_discovered_services(
        existing_services=[_service("A", "1")],
        discovered_services=[_service("B", "1")],
        run_plugin_names=EVERYTHING,
        only_new=False,
    )

    assert result.vanished == [_service("A", "1")]
    assert not result.old
    assert result.new == [_service("B", "1")]


def test_discover_run_plugin_names():

    result = _analyse_discovered_services(
        existing_services=[_service("A", "1"), _service("B", "1")],
        discovered_services=[_service("B", "2")],
        run_plugin_names={CheckPluginName("B")},
        only_new=False,
    )

    assert result.vanished == [_service("B", "1")]
    assert result.old == [_service("A", "1")]
    assert result.new == [_service("B", "2")]
