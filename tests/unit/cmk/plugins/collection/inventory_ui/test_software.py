#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.inventory_ui.v1_unstable import TextField
from cmk.plugins.collection.inventory_ui.software import node_software_packages


@pytest.mark.parametrize("column", ["version", "package_version"])
def test_versions_with_differently_split_parts_can_be_sorted(column: str) -> None:
    field = node_software_packages.table.columns[column]
    assert isinstance(field, TextField) and field.sort_key is not None

    assert sorted(["a1", "a.1"], key=field.sort_key) == ["a.1", "a1"]
