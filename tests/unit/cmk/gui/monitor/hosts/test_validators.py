#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.hosts._api._validators import (
    parse_host_search_query,
    parse_host_sort_options,
    validate_uniqueness,
)
from cmk.gui.monitor.hosts._models import HostSort, HostSortColumn, HostSortDirection


def test_validate_uniqueness() -> None:
    with pytest.raises(ValueError, match="Duplicate values are not allowed."):
        validate_uniqueness(["UP", "UP", "DOWN"])


class TestHostSearchQuery:
    def test_plain_value_is_kept(self) -> None:
        assert parse_host_search_query("web-server") == "web-server"

    def test_surrounding_whitespace_is_stripped(self) -> None:
        assert parse_host_search_query("  web-server  ") == "web-server"

    def test_inner_whitespace_is_kept(self) -> None:
        assert parse_host_search_query("  web server  ") == "web server"

    def test_newline_characters_are_removed(self) -> None:
        assert parse_host_search_query("web\nserver\r\n") == "webserver"

    def test_empty_value_is_no_filter(self) -> None:
        assert parse_host_search_query("") == ""

    def test_whitespace_only_value_is_no_filter(self) -> None:
        assert parse_host_search_query("   ") == ""

    def test_invalid_value_type(self) -> None:
        with pytest.raises(ValueError, match="Expected a search string"):
            parse_host_search_query(123)


class TestHostSort:
    def test_valid_sort_options(self) -> None:
        result = parse_host_sort_options(["name:asc", "state:desc"])
        assert result == [
            HostSort(column=HostSortColumn.NAME, direction=HostSortDirection.ASC),
            HostSort(column=HostSortColumn.STATE, direction=HostSortDirection.DESC),
        ]

    def test_invalid_options_type(self) -> None:
        with pytest.raises(ValueError, match="Expected a list of sort values"):
            parse_host_sort_options("name:asc")

    def test_invalid_option_type(self) -> None:
        with pytest.raises(ValueError, match="Expected a 'column:direction' string"):
            parse_host_sort_options([123])

    def test_invalid_column_value(self) -> None:
        with pytest.raises(ValueError, match="Unknown sort column"):
            parse_host_sort_options(["invalid:asc"])

    def test_invalid_direction_value(self) -> None:
        with pytest.raises(ValueError, match="Unknown sort direction"):
            parse_host_sort_options(["name:invalid"])

    def test_no_separator_present(self) -> None:
        with pytest.raises(ValueError, match="Expected a 'column:direction' value"):
            parse_host_sort_options(["nameasc"])

    def test_duplicate_column_values(self) -> None:
        with pytest.raises(ValueError, match="The following columns were duplicated: name"):
            parse_host_sort_options(["name:asc", "name:desc"])

    def test_duplicate_column_values_multiple(self) -> None:
        with pytest.raises(ValueError, match="The following columns were duplicated: name, alias"):
            parse_host_sort_options(["name:asc", "name:desc", "alias:asc", "alias:desc"])
