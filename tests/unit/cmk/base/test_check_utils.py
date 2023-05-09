#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Optional

from cmk.utils.type_defs import CheckPluginName
from cmk.base.check_utils import Service


def _service(plugin: str, item: Optional[str]) -> Service:
    return Service(
        check_plugin_name=CheckPluginName(plugin),
        item=item,
        description=f"test description {plugin}/{item}",
        parameters={},
    )


def test_service_sortable():

    assert sorted([
        _service("B", "b"),
        _service("A", "b"),
        _service("B", "a"),
        _service("A", None),
    ]) == [
        _service("A", None),
        _service("A", "b"),
        _service("B", "a"),
        _service("B", "b"),
    ]
