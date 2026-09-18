#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.livestatus_client.expressions import And, LqSafe
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.crashreports import Crashreports
from cmk.livestatus_client.tables.hosts import Hosts
from cmk.livestatus_client.tables.services import Services
from cmk.livestatus_client.types import Column, escape_filename


class TestEscapeFilename:
    def test_space_is_escaped(self) -> None:
        assert escape_filename("var/log/my file.log") == "var/log/my\\sfile.log"

    def test_backslash_is_escaped(self) -> None:
        assert escape_filename("back\\slash") == "back\\\\slash"

    def test_backslash_is_escaped_before_space(self) -> None:
        assert escape_filename("a\\ b") == "a\\\\\\sb"

    def test_plain_filename_is_unchanged(self) -> None:
        assert escape_filename("var/log/messages") == "var/log/messages"

    def test_newline_is_not_escaped_and_rejected_by_dynamic(self) -> None:
        escaped = escape_filename("evil\nFilter: name = injected")
        with pytest.raises(ValueError, match="Invalid Livestatus Query string"):
            Hosts.mk_logwatch_file.dynamic("file", f"myhost/{escaped}")


class TestDynamic:
    def test_creates_column_bound_to_table(self) -> None:
        column = Services.prediction_file.dynamic("file", "metric/day-123-upper")
        assert isinstance(column, Column)
        assert column.name == "prediction_file:file:metric/day-123-upper"
        assert column.type == "blob"
        assert column.table is Services

    def test_multiple_arguments_are_joined_with_colons(self) -> None:
        column = Hosts.rrddata.dynamic("cpu", "util", 1234, 5678, 60)
        assert column.name == "rrddata:cpu:util:1234:5678:60"

    def test_accepts_lq_safe_arguments(self) -> None:
        column = Crashreports.file.dynamic(LqSafe("file"), LqSafe("gui/crash.info"))
        assert column.name == "file:file:gui/crash.info"

    def test_requires_at_least_one_argument(self) -> None:
        with pytest.raises(ValueError, match="requires at least one argument"):
            Services.prediction_file.dynamic("file")

    def test_escaped_filename_is_accepted(self) -> None:
        column = Hosts.mk_logwatch_file.dynamic(
            "file", f"myhost/{escape_filename('var/log/my file.log')}"
        )
        assert column.name == "mk_logwatch_file:file:myhost/var/log/my\\sfile.log"

    def test_unescaped_filename_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="contains whitespace"):
            Hosts.mk_logwatch_file.dynamic("file", "myhost/var/log/my file.log")

    def test_rejects_newline_injection(self) -> None:
        with pytest.raises(ValueError, match="Invalid Livestatus Query string"):
            Services.prediction_file.dynamic("file", "path\nFilter: host_name = injected")

    def test_rejects_whitespace_in_arguments(self) -> None:
        with pytest.raises(ValueError, match="contains whitespace"):
            Services.prediction_file.dynamic("file", "path another_column")

    def test_rejects_whitespace_in_title(self) -> None:
        with pytest.raises(ValueError, match="contains whitespace"):
            Services.prediction_file.dynamic("fi le", "path")

    def test_rejects_colon_in_title(self) -> None:
        with pytest.raises(ValueError, match="Invalid dynamic column title"):
            Services.prediction_file.dynamic("file:extra", "path")

    def test_rejects_empty_title(self) -> None:
        with pytest.raises(ValueError, match="Invalid dynamic column title"):
            Services.prediction_file.dynamic("", "path")


class TestQueryWithDynamicColumns:
    def test_compile(self) -> None:
        query = Query(
            [Services.prediction_file.dynamic("file", "metric/day-123-upper")],
            And(
                Services.host_name == "heute",
                Services.description == "CPU",
            ),
        )
        assert query.compile() == (
            "GET services\n"
            "Columns: prediction_file:file:metric/day-123-upper\n"
            "Filter: host_name = heute\n"
            "Filter: description = CPU\n"
            "And: 2"
        )

    def test_blob_dynamic_column_does_not_support_json_format(self) -> None:
        query = Query([Services.prediction_file.dynamic("file", "some/path")])
        assert not query.supports_json_format()

    def test_list_dynamic_column_supports_json_format(self) -> None:
        query = Query([Services.rrddata.dynamic("cpu", "util", 1234, 5678, 60)])
        assert query.supports_json_format()

    def test_rendered_column_uses_title_as_response_key(self) -> None:
        column = Services.prediction_file.dynamic("file", "metric/day-123-upper")
        assert column.query_name == "file"
