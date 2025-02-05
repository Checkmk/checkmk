#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.utils.filter


def test_requested_filter_is_not_default__empty_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cmk.gui.utils.filter, "request", _RequestStub(args=[], vars={}))

    value = cmk.gui.utils.filter.check_if_non_default_filter_in_request({})
    expected = False

    assert value == expected


@pytest.mark.parametrize(
    "args, expected",
    [
        pytest.param(["match_op"], False, id="matched *_op var detected"),
        pytest.param(["non-matching-arg"], True, id="non-matched var is ok"),
    ],
)
def test_requested_filter_is_not_default__request_args(
    args: list[str], expected: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = _RequestStub(args=args, vars={"filled_in": "filter", "_active": "foo;bar"})
    monkeypatch.setattr(cmk.gui.utils.filter, "request", stub)

    value = cmk.gui.utils.filter.check_if_non_default_filter_in_request({})

    assert value == expected


@pytest.mark.parametrize(
    "vars, expected",
    [
        pytest.param({"filled_in": "filter"}, True, id="_active not present in vars"),
        pytest.param({"filled_in": "filter", "_active": "foo;"}, True, id="_active set and found"),
    ],
)
def test_requested_filter_is_not_default__request_vars_with_static_ctx(
    vars: dict[str, str], expected: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = _RequestStub(args=[], vars=vars)
    monkeypatch.setattr(cmk.gui.utils.filter, "request", stub)

    value = cmk.gui.utils.filter.check_if_non_default_filter_in_request({"foo": {"hello": "world"}})

    assert value == expected


@pytest.mark.parametrize(
    "vars, ctx, expected",
    [
        pytest.param(
            {"filled_in": "filter", "_active": "foo;"},
            {"foo": {}},
            False,
            id="no sub keys matched in context value",
        ),
        pytest.param(
            {"filled_in": "filter", "_active": "foo;"},
            {"foo": {"my_count": "1"}},
            False,
            id="*_count matched var detected in context",
        ),
        pytest.param(
            {"filled_in": "filter", "_active": "foo;", "foo": "value"},
            {"foo": {}},
            True,
            id="no sub keys matched but foo found in request vars",
        ),
        pytest.param(
            {"filled_in": "filter", "_active": "foo;", "foo": "value"},
            {},
            True,
            id="foo found in _active keys but not in context (branch #1)",
        ),
        pytest.param(
            {"filled_in": "filter", "_active": "foo;"},
            {"not_found": {}},
            True,
            id="foo found in _active keys but not in context (branch #2)",
        ),
        pytest.param(
            {
                "filled_in": "filter",
                "_active": "host_labels",
                "host_labels_count": "1",
                "host_labels_indexof_1": "1",
                "host_labels_1_bool": "and",
                "host_labels_1_vs_count": "2",
                "host_labels_1_vs_indexof_1": "1",
                "host_labels_1_vs_1_bool": "and",
                "host_labels_1_vs_1_vs": "cmk/os_family:linux",
                "host_labels_1_vs_indexof_2": "2",
                "host_labels_1_vs_2_bool": "and",
                "name": "linux_hosts_overview",
            },
            {
                "host_labels": {
                    "host_labels_count": "1",
                    "host_labels_1_vs_count": "1",
                    "host_labels_1_bool": "and",
                    "host_labels_indexof_1": "1",
                    "host_labels_1_vs_1_bool": "and",
                    "host_labels_1_vs_1_vs": "cmk/os_family:linux",
                    "host_labels_1_vs_indexof_1": "1",
                },
            },
            False,
            id="complex multivalue with operator is default",
        ),
        pytest.param(
            {
                "filled_in": "filter",
                "_active": "host_labels",
                "host_labels_count": "1",
                "host_labels_indexof_1": "1",
                "host_labels_1_bool": "and",
                "host_labels_1_vs_count": "2",
                "host_labels_1_vs_indexof_1": "1",
                "host_labels_1_vs_1_bool": "not",
                "host_labels_1_vs_1_vs": "cmk/os_family:linux",
                "host_labels_1_vs_indexof_2": "2",
                "host_labels_1_vs_2_bool": "and",
                "name": "linux_hosts_overview",
            },
            {
                "host_labels": {
                    "host_labels_count": "1",
                    "host_labels_1_vs_count": "1",
                    "host_labels_1_bool": "and",
                    "host_labels_indexof_1": "1",
                    "host_labels_1_vs_1_bool": "and",
                    "host_labels_1_vs_1_vs": "cmk/os_family:linux",
                    "host_labels_1_vs_indexof_1": "1",
                },
            },
            True,
            id="complex multivalue with operator differs at one operator",
        ),
        pytest.param(
            {
                "filled_in": "filter",
                "_active": "host_labels",
                "host_labels_count": 1,
                "host_labels_indexof_1": 1,
                "host_labels_1_bool": "and",
                "host_labels_1_vs_count": 3,
                "host_labels_1_vs_indexof_1": 1,
                "host_labels_1_vs_1_bool": "and",
                "host_labels_1_vs_1_vs": "cmk/os_family:linux",
                "host_labels_1_vs_indexof_2": 2,
                "host_labels_1_vs_2_bool": "or",
                "host_labels_1_vs_2_vs": "cmk/os_name:Ubuntu",
                "host_labels_1_vs_indexof_3": 3,
                "host_labels_1_vs_3_bool": "or",
                "name": "linux_hosts_overview",
            },
            {
                "host_labels": {
                    "host_labels_count": "1",
                    "host_labels_1_vs_count": "1",
                    "host_labels_1_bool": "and",
                    "host_labels_indexof_1": "1",
                    "host_labels_1_vs_1_bool": "and",
                    "host_labels_1_vs_1_vs": "cmk/os_family:linux",
                    "host_labels_1_vs_indexof_1": "1",
                },
            },
            True,
            id="complex multivalue with additional non-default value",
        ),
        pytest.param(
            {
                "filled_in": "filter",
                "_active": "foo;",
                "name": "all_linux_hosts",
                "view_name": "all_hosts",
            },
            {},
            False,
            id="given _NON_DEFAULT_KEYS_TO_IGNORE getting ignored correctly",
        ),
    ],
)
def test_requested_filter_is_not_default__request_vars_with_dynamic_ctx(
    vars: dict[str, str],
    ctx: dict[str, dict[str, str]],
    expected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cmk.gui.utils.filter, "request", _RequestStub(args=[], vars=vars))

    value = cmk.gui.utils.filter.check_if_non_default_filter_in_request(ctx)

    assert value == expected


class _RequestStub:
    """Stub meant for mocking out the Flask request singleton."""

    def __init__(self, *, args: list[str], vars: dict[str, str]) -> None:
        self.args = {k: "" for k in args}
        self._vars = vars

    def var(self, key: str) -> str | None:
        return self._vars.get(key, None)
