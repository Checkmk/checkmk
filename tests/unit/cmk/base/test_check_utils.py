#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.checkengine.check_table import ConfiguredService
from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.parameters import TimespecificParameters


def _service(plugin: str, item: str | None) -> ConfiguredService:
    return ConfiguredService(
        check_plugin_name=CheckPluginName(plugin),
        item=item,
        description=f"test description {plugin}/{item}",
        parameters=TimespecificParameters(),
        discovered_parameters={},
        service_labels={},
        is_enforced=False,
    )


def test_service_sortable() -> None:
    assert sorted(
        [
            _service("B", "b"),
            _service("A", "b"),
            _service("B", "a"),
            _service("A", None),
        ],
        key=lambda s: s.sort_key(),
    ) == [
        _service("A", None),
        _service("A", "b"),
        _service("B", "a"),
        _service("B", "b"),
    ]
