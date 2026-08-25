#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.gui.monitor.hosts._folder import MonitorFolders, SetupFolders
from cmk.gui.monitor.hosts._impl import (
    _build_primary_sort,
    _build_query_filter,
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


_TITLES = {"web_dmz": "Web DMZ", "network": "Netzwerk"}


def _folders() -> MonitorFolders:
    """A `MonitorFolders` titling two folders, the way Setup's functions are wired in."""
    folders = MonitorFolders()
    folders.use_setup_source(
        SetupFolders(title_of=_TITLES.get, all_titles=lambda: _TITLES),
    )
    return folders


def test_build_query_filter_without_a_query_matches_everything() -> None:
    assert _build_query_filter("", frozenset(HostOptionalField), _folders()).render() == []


def test_build_query_filter_searches_the_name_of_a_table_without_optional_columns() -> None:
    assert _build_query_filter("web", frozenset(), _folders()).render() == [
        ("Filter", "name ~~ web")
    ]


def test_build_query_filter_searches_every_shown_text_field() -> None:
    """The folder is searched by its title, so the query reaches it as that folder's file."""
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
        _folders(),
    ).render() == [
        ("Filter", "name ~~ web"),
        ("Filter", "alias ~~ web"),
        ("Filter", "address ~~ web"),
        ("Filter", "filename = /wato/web_dmz/hosts.mk"),
        ("Or", "4"),
    ]


def test_build_query_filter_leaves_out_the_folder_no_title_carries() -> None:
    assert _build_query_filter(
        "no such folder", frozenset({HostOptionalField.FOLDER}), _folders()
    ).render() == [("Filter", "name ~~ no such folder")]


def test_build_query_filter_leaves_out_a_hidden_field() -> None:
    assert _build_query_filter(
        "web", frozenset({HostOptionalField.ALIAS}), _folders()
    ).render() == [
        ("Filter", "name ~~ web"),
        ("Filter", "alias ~~ web"),
        ("Or", "2"),
    ]
