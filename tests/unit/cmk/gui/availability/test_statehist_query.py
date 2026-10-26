#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.computation import (
    apply_logrow_limit,
    build_statehist_columns,
    build_statehist_headers,
)
from cmk.gui.availability.type_defs import AVHostOrServiceObjectSpec, AVSpan

_AV_OBJECT: AVHostOrServiceObjectSpec = (SiteId("site1"), HostName("myhost"), "CPU load")


def _spans_for_site(site: str, count: int) -> list[AVSpan]:
    return [cast(AVSpan, {"site": site}) for _ in range(count)]


def test_output_column_is_requested_with_include_output() -> None:
    assert "log_output" in build_statehist_columns(True, False, [], None)


def test_output_column_is_omitted_without_include_output() -> None:
    assert "log_output" not in build_statehist_columns(False, False, [], None)


def test_long_output_columns_are_requested_with_include_long_output() -> None:
    columns = build_statehist_columns(False, True, [], None)
    assert {"long_log_output", "service_check_command", "service_custom_variables"} <= set(columns)


def test_long_output_columns_are_omitted_without_include_long_output() -> None:
    columns = build_statehist_columns(False, False, [], None)
    assert not {"long_log_output", "service_check_command", "service_custom_variables"} & set(
        columns
    )


def test_display_name_column_is_requested_when_labelling_by_display_name() -> None:
    assert "service_display_name" in build_statehist_columns(
        False, False, ["use_display_name"], None
    )


def test_alias_column_is_requested_when_labelling_with_alias() -> None:
    assert "host_alias" in build_statehist_columns(False, False, ["show_alias"], None)


def test_group_column_is_requested_when_grouping_by_service_groups() -> None:
    assert "service_groups" in build_statehist_columns(False, False, [], "service_groups")


def test_no_group_column_is_requested_when_grouping_by_host() -> None:
    assert "host" not in build_statehist_columns(False, False, [], "host")


def test_query_is_restricted_to_the_time_range() -> None:
    headers = build_statehist_headers("host", None, (1000, 2000), 30, "")
    assert headers.startswith("Filter: time >= 1000\nFilter: time < 2000\n")


def test_query_carries_the_timelimit() -> None:
    headers = build_statehist_headers("host", None, (0, 100), 30, "")
    assert "Timelimit: 30\n" in headers


def test_caller_filters_are_appended_to_the_query() -> None:
    headers = build_statehist_headers("host", None, (0, 100), 30, "Filter: host_name = x\n")
    assert headers.endswith("Filter: host_name = x\n")


def test_host_query_selects_rows_without_service() -> None:
    headers = build_statehist_headers("host", None, (0, 100), 30, "")
    assert "Filter: service_description =\n" in headers


def test_service_query_selects_rows_with_service() -> None:
    headers = build_statehist_headers("service", None, (0, 100), 30, "")
    assert "Filter: service_description !=\n" in headers


def test_host_query_for_an_object_selects_exactly_that_object() -> None:
    headers = build_statehist_headers("host", _AV_OBJECT, (0, 100), 30, "")
    assert "Filter: host_name = myhost\nFilter: service_description = CPU load\n" in headers
    assert "Filter: service_description =\n" not in headers


def test_service_query_for_an_object_selects_exactly_that_object() -> None:
    headers = build_statehist_headers("service", _AV_OBJECT, (0, 100), 30, "")
    assert "Filter: host_name = myhost\nFilter: service_description = CPU load\n" in headers
    assert "Filter: service_description !=\n" not in headers


def test_without_limit_no_span_is_dropped() -> None:
    spans = _spans_for_site("site1", 1000)
    assert apply_logrow_limit(spans, None) == (spans, False)


def test_sites_below_the_limit_keep_all_spans_even_if_their_sum_exceeds_it() -> None:
    # CMK-8277: the livestatus limit applies per site, not to the sum of all sites.
    spans = _spans_for_site("site1", 5) + _spans_for_site("site2", 5) + _spans_for_site("site3", 5)
    assert apply_logrow_limit(spans, 11) == (spans, False)


def test_a_site_at_the_limit_drops_the_last_span() -> None:
    spans = _spans_for_site("site1", 5) + _spans_for_site("site2", 11)
    assert apply_logrow_limit(spans, 11) == (spans[:-1], True)


def test_several_sites_at_the_limit_drop_only_the_last_span() -> None:
    spans = _spans_for_site("site1", 11) + _spans_for_site("site2", 11)
    assert apply_logrow_limit(spans, 11) == (spans[:-1], True)
