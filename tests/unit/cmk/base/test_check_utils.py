#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Optional

import pytest

from cmk.utils.type_defs import CheckPluginName, LegacyCheckParameters

from cmk.base.check_utils import Service
from cmk.base.discovered_labels import ServiceLabel


def test_discovered_service_init() -> None:
    ser = Service(CheckPluginName("abc"), "Item", "ABC Item", None)
    assert ser.check_plugin_name == CheckPluginName("abc")
    assert ser.item == "Item"
    assert ser.description == "ABC Item"
    assert ser.parameters is None
    assert ser.service_labels == {}

    ser = Service(
        CheckPluginName("abc"),
        "Item",
        "ABC Item",
        None,
        {"läbel": ServiceLabel("läbel", "lübel")},
    )

    assert ser.service_labels == {"läbel": ServiceLabel("läbel", "lübel")}

    with pytest.raises(AttributeError):
        ser.xyz = "abc"  # type: ignore[attr-defined] # pylint: disable=assigning-non-slot


def test_discovered_service_eq() -> None:
    ser1: Service[LegacyCheckParameters] = Service(CheckPluginName("abc"), "Item", "ABC Item", None)
    ser2: Service[LegacyCheckParameters] = Service(CheckPluginName("abc"), "Item", "ABC Item", None)
    ser3: Service[LegacyCheckParameters] = Service(CheckPluginName("xyz"), "Item", "ABC Item", None)
    ser4: Service[LegacyCheckParameters] = Service(CheckPluginName("abc"), "Xtem", "ABC Item", None)
    ser5: Service[LegacyCheckParameters] = Service(CheckPluginName("abc"), "Item", "ABC Item", [""])

    assert ser1 == ser1  # pylint: disable=comparison-with-itself
    assert ser1 == ser2
    assert ser1 != ser3
    assert ser1 != ser4
    assert ser1 == ser5

    assert ser1 in [ser1]
    assert ser1 in [ser2]
    assert ser1 not in [ser3]
    assert ser1 not in [ser4]
    assert ser1 in [ser5]

    assert ser1 in {ser1}
    assert ser1 in {ser2}
    assert ser1 not in {ser3}
    assert ser1 not in {ser4}
    assert ser1 in {ser5}


def _service(plugin: str, item: Optional[str]) -> Service:
    return Service(
        check_plugin_name=CheckPluginName(plugin),
        item=item,
        description=f"test description {plugin}/{item}",
        parameters={},
    )


def test_service_sortable():

    assert sorted(
        [
            _service("B", "b"),
            _service("A", "b"),
            _service("B", "a"),
            _service("A", None),
        ]
    ) == [
        _service("A", None),
        _service("A", "b"),
        _service("B", "a"),
        _service("B", "b"),
    ]
