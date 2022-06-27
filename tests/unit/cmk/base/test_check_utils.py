#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import CheckPluginName

from cmk.base.check_utils import ConfiguredService


def _service(plugin: str, item: Optional[str]) -> ConfiguredService:
    return ConfiguredService(
        check_plugin_name=CheckPluginName(plugin),
        item=item,
        description=f"test description {plugin}/{item}",
        parameters=TimespecificParameters(),
        discovered_parameters={},
        service_labels={},
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
