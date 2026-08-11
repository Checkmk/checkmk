#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.gui.monitor.hosts._impl import (
    _build_primary_sort,
    _OPTIONAL_COLUMNS,
    _SORT_COLUMN_FIELDS,
    _wato_folder_from_filename,
)
from cmk.gui.monitor.hosts._models import (
    HostOptionalField,
    HostSort,
    HostSortColumn,
    HostSortDirection,
)


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
            [HostSort(HostSortColumn.SITE_ID, HostSortDirection.ASC)],
            "OrderBy: name asc",
            id="site_id falls back to the default primary sort, site isn't a real Livestatus column",
        ),
        pytest.param(
            [
                HostSort(HostSortColumn.SITE_ID, HostSortDirection.ASC),
                HostSort(HostSortColumn.NAME, HostSortDirection.DESC),
            ],
            "OrderBy: name asc",
            id="site_id as the first sorter still falls back, even with a real sorter behind it",
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


def test_every_optional_field_names_the_columns_it_needs() -> None:
    """A new HostOptionalField must say which livestatus columns it reads, or it reads none."""
    assert set(_OPTIONAL_COLUMNS) == set(HostOptionalField)


def test_every_sort_column_maps_to_a_field_or_is_always_read() -> None:
    """Sorting happens in Python, so a sort column must either be mandatory or ask for its field."""
    # `site` is synthesized by the multisite connection rather than queried, so sorting on it needs
    # no column of its own - same as the two the query always reads.
    always_read = {HostSortColumn.NAME, HostSortColumn.STATE, HostSortColumn.SITE_ID}
    assert set(_SORT_COLUMN_FIELDS) | always_read == set(HostSortColumn)
