#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.services._api._validators import (
    parse_service_search_query,
    parse_service_sort_options,
    validate_uniqueness,
)
from cmk.gui.monitor.services._models import ServiceSort, ServiceSortColumn, ServiceSortDirection


def test_validate_uniqueness() -> None:
    with pytest.raises(ValueError, match="Duplicate values are not allowed."):
        validate_uniqueness(["OK", "OK", "WARN"])


class TestServiceSearchQuery:
    def test_plain_value_is_kept(self) -> None:
        assert parse_service_search_query("CPU") == "CPU"

    def test_surrounding_whitespace_is_stripped(self) -> None:
        assert parse_service_search_query("  CPU  ") == "CPU"

    def test_inner_whitespace_is_kept(self) -> None:
        assert parse_service_search_query("  CPU load  ") == "CPU load"

    def test_newline_characters_are_removed(self) -> None:
        assert parse_service_search_query("CPU\nload\r\n") == "CPUload"

    def test_empty_value_is_no_filter(self) -> None:
        assert parse_service_search_query("") == ""

    def test_whitespace_only_value_is_no_filter(self) -> None:
        assert parse_service_search_query("   ") == ""

    def test_invalid_value_type(self) -> None:
        with pytest.raises(ValueError, match="Expected a search string"):
            parse_service_search_query(123)


class TestServiceSort:
    def test_valid_sort_options(self) -> None:
        result = parse_service_sort_options(["name:asc", "state:desc"])
        assert result == [
            ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.ASC),
            ServiceSort(column=ServiceSortColumn.STATE, direction=ServiceSortDirection.DESC),
        ]

    def test_empty_options_are_allowed(self) -> None:
        assert parse_service_sort_options([]) == []

    def test_invalid_options_type(self) -> None:
        with pytest.raises(ValueError, match="Expected a list of sort values"):
            parse_service_sort_options("name:asc")

    def test_invalid_option_type(self) -> None:
        with pytest.raises(ValueError, match="Expected a 'column:direction' string"):
            parse_service_sort_options([123])

    def test_invalid_column_value(self) -> None:
        with pytest.raises(ValueError, match="Unknown sort column"):
            parse_service_sort_options(["invalid:asc"])

    def test_host_only_column_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown sort column"):
            parse_service_sort_options(["address:asc"])

    def test_invalid_direction_value(self) -> None:
        with pytest.raises(ValueError, match="Unknown sort direction"):
            parse_service_sort_options(["name:invalid"])

    def test_no_separator_present(self) -> None:
        with pytest.raises(ValueError, match="Expected a 'column:direction' value"):
            parse_service_sort_options(["nameasc"])

    def test_duplicate_column_values(self) -> None:
        with pytest.raises(ValueError, match="The following columns were duplicated: name"):
            parse_service_sort_options(["name:asc", "name:desc"])

    def test_duplicate_column_values_multiple(self) -> None:
        with pytest.raises(
            ValueError, match="The following columns were duplicated: name, summary"
        ):
            parse_service_sort_options(
                ["name:asc", "name:desc", "summary:asc", "summary:desc"],
            )
