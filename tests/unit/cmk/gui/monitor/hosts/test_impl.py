#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Sequence

import pytest

from cmk.gui.monitor.hosts._impl import (
    _build_primary_sort,
    _build_query_filter,
    _folder_pattern,
    _OPTIONAL_COLUMNS,
    _SORT_COLUMN_FIELDS,
)
from cmk.gui.monitor.hosts._models import (
    HostOptionalField,
    HostSort,
    HostSortColumn,
    HostSortDirection,
)


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


@pytest.mark.parametrize(
    "filename, query, expected",
    [
        pytest.param("/wato/network/switches/hosts.mk", "switch", True, id="folder name"),
        pytest.param("/wato/network/hosts.mk", "network", True, id="folder right below the root"),
        pytest.param("/wato/network/switches/hosts.mk", "network/sw", True, id="partial path"),
        pytest.param("/wato/network/hosts.mk", "/network", True, id="path as the table shows it"),
        pytest.param("/wato/network/hosts.mk", "NETWORK", True, id="different case"),
        pytest.param("/wato/network/hosts.mk", "wato", False, id="the config path is not a folder"),
        pytest.param("/wato/network/hosts.mk", "hosts", False, id="the file name is not a folder"),
        pytest.param("/wato/network/hosts.mk", "mk", False, id="the file suffix is not a folder"),
        pytest.param("/wato/hosts.mk", "wato", False, id="the root folder has no name to match"),
        pytest.param(
            "/omd/sites/heute/etc/nagios/conf.d/hosts.mk",
            "nagios",
            False,
            id="a host not managed via Setup has no folder",
        ),
    ],
)
def test_folder_pattern_matches_only_the_folder_path(
    filename: str, query: str, expected: bool
) -> None:
    assert bool(re.search(_folder_pattern(query), filename, re.IGNORECASE)) is expected


def test_build_query_filter_without_a_query_matches_everything() -> None:
    assert _build_query_filter("", frozenset(HostOptionalField)).render() == []


def test_build_query_filter_searches_the_name_of_a_table_without_optional_columns() -> None:
    assert _build_query_filter("web", frozenset()).render() == [("Filter", "name ~~ web")]


def test_build_query_filter_searches_every_shown_text_field() -> None:
    assert _build_query_filter(
        "web",
        frozenset(
            {
                HostOptionalField.ALIAS,
                HostOptionalField.ADDRESS,
                HostOptionalField.FOLDER,
                HostOptionalField.LAST_CHECK,
            }
        ),
    ).render() == [
        ("Filter", "name ~~ web"),
        ("Filter", "alias ~~ web"),
        ("Filter", "address ~~ web"),
        ("Filter", r"filename ~~ ^/wato.*web.*/hosts\.mk$"),
        ("Or", "4"),
    ]


def test_build_query_filter_leaves_out_a_hidden_field() -> None:
    assert _build_query_filter("web", frozenset({HostOptionalField.ALIAS})).render() == [
        ("Filter", "name ~~ web"),
        ("Filter", "alias ~~ web"),
        ("Or", "2"),
    ]
