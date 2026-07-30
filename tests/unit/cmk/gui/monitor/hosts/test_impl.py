#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.gui.monitor.hosts._impl import _build_primary_sort, _wato_folder_from_filename
from cmk.gui.monitor.hosts._models import HostSort, HostSortColumn, HostSortDirection


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("/wato/hosts.mk", "/"),
        ("/wato/network/switches/hosts.mk", "/network/switches"),
        ("/wato/network/hosts.mk", "/network"),
        ("/omd/sites/heute/etc/nagios/conf.d/hosts.mk", ""),
        ("/wato/network/switches/other.mk", ""),
    ],
)
def test_wato_folder_from_filename(filename: str, expected: str) -> None:
    assert _wato_folder_from_filename(filename) == expected


@pytest.mark.parametrize(
    "sorters, expected",
    [
        pytest.param(
            [],
            "OrderBy: name asc",
            id="default fallback",
        ),
        pytest.param(
            [HostSort(HostSortColumn.STATE, HostSortDirection.DESC)],
            "OrderBy: state desc",
            id="descending order",
        ),
        pytest.param(
            [HostSort(HostSortColumn.NAME, HostSortDirection.ASC)],
            "OrderBy: name asc natural",
            id="natural sort",
        ),
        pytest.param(
            [HostSort(HostSortColumn.FOLDER, HostSortDirection.ASC)],
            "OrderBy: filename asc natural",
            id="folder/filename handling",
        ),
        pytest.param(
            [
                HostSort(HostSortColumn.STATE, HostSortDirection.DESC),
                HostSort(HostSortColumn.NAME, HostSortDirection.ASC),
                HostSort(HostSortColumn.FOLDER, HostSortDirection.ASC),
            ],
            "OrderBy: state desc",
            id="only first sorter used",
        ),
    ],
)
def test_build_primary_sort(sorters: Sequence[HostSort], expected: str) -> None:
    assert _build_primary_sort(sorters) == expected
