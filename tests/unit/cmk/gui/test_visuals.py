#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.gui.visuals import filters_allowed_for_info, filters_allowed_for_infos
from cmk.gui.visuals.filter import AjaxDropdownFilter, Filter
from cmk.web.utils.request_cache import RequestCache


def test_get_filter() -> None:
    f = visuals.get_filter("hostregex")
    assert isinstance(f, Filter)


def test_get_not_existing_filter() -> None:
    with pytest.raises(KeyError):
        visuals.get_filter("dingelig")


# TODO: The Next two are really poor tests. Put something better
def test_filters_allowed_for_info() -> None:
    allowed = dict(filters_allowed_for_info("host"))
    assert isinstance(allowed["host"], AjaxDropdownFilter)
    assert "service" not in allowed


def test_filters_allowed_for_infos() -> None:
    allowed = filters_allowed_for_infos(["host", "service"])
    assert isinstance(allowed["host"], AjaxDropdownFilter)
    assert isinstance(allowed["service"], AjaxDropdownFilter)


@pytest.mark.parametrize(
    "context,expected_vars",
    [
        # No single context, use multi filter
        ({"filter_name": {"filter_var": "eee"}}, [("filter_var", "eee")]),
        # Single host context
        ({"host": {"host": "abc"}}, [("host", "abc")]),
        # Single host context, and other filters
        ({"host": {"host": "abc"}, "bla": {"blub": "ble"}}, [("blub", "ble"), ("host", "abc")]),
        # Single host context, missing filter -> no failure
        ({}, []),
        # Single host + service context
        (
            {"host": {"host": "abc"}, "service": {"service": "äää"}},
            [("host", "abc"), ("service", "äää")],
        ),
    ],
)
def test_context_to_uri_vars(
    context: VisualContext, expected_vars: Sequence[tuple[str, str]]
) -> None:
    context_vars = visuals.context_to_uri_vars(context)
    assert sorted(context_vars) == sorted(expected_vars)


@pytest.mark.parametrize(
    "infos,uri_vars,expected_context",
    [
        # No single context, no filter
        (["host"], [("abc", "dingeling")], {}),
        # Single host context
        (["host"], [("host", "aaa")], {"host": {"host": "aaa"}}),
        # Single host context with site hint
        # -> add site and siteopt (Why? Was like this in 1.6...)
        (
            ["host"],
            [("host", "aaa"), ("site", "abc")],
            {"host": {"host": "aaa"}, "site": {"site": "abc"}, "siteopt": {"site": "abc"}},
        ),
        # Single host context -> not set
        (["host"], [], {}),
        # Single host context -> empty set
        (["host"], [("host", "")], {}),
        # Single host context with non-ascii char
        (["host"], [("host", "äbc")], {"host": {"host": "äbc"}}),
        # Single host context, multiple services
        (
            ["host", "service"],
            [("host", "aaa"), ("service_regex", "äbc")],
            {"host": {"host": "aaa"}, "serviceregex": {"service_regex": "äbc"}},
        ),
        # multiple services
        (
            ["service", "host"],
            [("host", "aaa"), ("service_regex", "äbc")],
            {
                "serviceregex": {"service_regex": "äbc"},
                "host": {"host": "aaa"},
            },
        ),
        # multiple services, ignore filters of unrelated infos
        (
            ["service"],
            [("host", "aaa"), ("service_regex", "äbc")],
            {
                "serviceregex": {"service_regex": "äbc"},
            },
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_get_context_from_uri_vars(
    infos: SingleInfos, uri_vars: Sequence[tuple[str, str]], expected_context: VisualContext
) -> None:
    for key, val in uri_vars:
        request.set_var(key, val)

    context = visuals.get_context_from_uri_vars(infos)
    assert context == expected_context


@pytest.mark.parametrize(
    "uri_vars,infos,context_vis,expected_context",
    [
        # Single host context, set via URL, with some service filter, set via context
        (
            [("host", "aaa")],
            ["host", "service"],
            {"service_regex": {"serviceregex": "abc"}},
            {
                "host": {"host": "aaa"},
                "service_regex": {"serviceregex": "abc"},
            },
        ),
        # Single host context, set via context and URL
        (
            [("host", "aaa")],
            ["host", "service"],
            {
                "host": {"host": "from_context"},
            },
            {"host": {"host": "from_context"}},
        ),
        # No single context with some host & service filter
        (
            [("host", "aaa")],
            ["host", "service"],
            {"service_regex": {"serviceregex": "abc"}},
            {
                "host": {"host": "aaa"},
                "service_regex": {"serviceregex": "abc"},
            },
        ),
        # No single context with some host filter from URL
        (
            [("host", "aaa")],
            ["host", "service"],
            {},
            {
                "host": {"host": "aaa"},
            },
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_get_merged_context(
    uri_vars: Sequence[tuple[str, str]],
    infos: SingleInfos | None,
    context_vis: VisualContext,
    expected_context: VisualContext,
) -> None:
    for key, val in uri_vars:
        request.set_var(key, val)

    url_context = visuals.get_context_from_uri_vars(infos)
    context = visuals.get_merged_context(url_context, context_vis)

    assert context == expected_context


def test_get_missing_single_infos_has_context() -> None:
    assert (
        visuals.get_missing_single_infos(single_infos=["host"], context={"host": {"host": "abc"}})
        == set()
    )


def test_get_missing_single_infos_missing_context() -> None:
    assert visuals.get_missing_single_infos(single_infos=["host"], context={}) == {"host"}


def test_get_context_specs_only_host_and_service_info() -> None:
    result = visuals.get_context_specs(["host"], ["host", "service"], RequestCache(Config()))
    assert [r[0] for r in result] == [
        "host",
        "service",
    ]
