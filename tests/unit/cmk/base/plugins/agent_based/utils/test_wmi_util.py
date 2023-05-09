#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes.wmi import WMITable  # type: ignore[attr-defined]
# mypy can not handle globals ignore in .wmi https://github.com/python/mypy/issues/9318


def test_wmi_table_repr():
    # attention, this data is only for checking the __repr__, it is probably no
    # useful information for WMITable implementation!
    table = WMITable("name", ["first header", "second HEADER"], None, 123, ["row1", "row2"])
    assert table.__repr__(
    ) == "WMITable('name', ['firstheader', 'secondheader'], None, 123, ['row1', 'row2'], [])"
