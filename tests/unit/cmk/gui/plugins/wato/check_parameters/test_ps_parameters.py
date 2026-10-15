#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters.ps import (
    _valuespec_discovery_hr_processes_rules,
    _valuespec_inventory_processes_rules,
    forbid_re_delimiters_inside_groups,
    validate_process_discovery_descr_option,
)


@pytest.mark.parametrize("pattern", ["(test)$", "foo\\b", "^bar", "\\bfoo\\b", "(a)\\b"])
def test_validate_ps_allowed_regex(pattern: str) -> None:
    assert forbid_re_delimiters_inside_groups(pattern, "") is None


@pytest.mark.parametrize("pattern", ["(test$)", "(foo\\b)", "(^bar)", "(\\bfoo\\b)"])
def test_validate_ps_forbidden_regex(pattern: str) -> None:
    with pytest.raises(MKUserError):
        forbid_re_delimiters_inside_groups(pattern, "")


@pytest.mark.parametrize("description", ["%s%5"])
def test_validate_process_discovery_descr_option(
    description: str,
) -> None:
    with pytest.raises(MKUserError):
        validate_process_discovery_descr_option(description, "")


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param({"descr": "%s", "match": None}, id="match-all"),
        pytest.param({"descr": "%s", "match": "/usr/bin/foo"}, id="exact-name"),
        pytest.param({"descr": "%s %s", "match": "~(foo)"}, id="too-few-groups"),
        pytest.param({"descr": "%2", "match": "~(foo)"}, id="numbered-out-of-range"),
    ],
)
def test_process_discovery_rule_rejects_missing_groups(rule: dict[str, object]) -> None:
    with pytest.raises(MKUserError):
        _valuespec_inventory_processes_rules().validate_value(
            {**rule, "default_params": {"cpu_rescale_max": True}}, ""
        )


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param({"descr": "%s", "match": "~(foo.*)"}, id="one-group"),
        pytest.param({"descr": "%2 %1", "match": "~(a)(b)"}, id="numbered-groups"),
        pytest.param({"descr": "%u", "match": None}, id="user-only"),
        pytest.param({"descr": "foo", "match": "/usr/bin/foo"}, id="no-placeholder"),
    ],
)
def test_process_discovery_rule_accepts_matching_groups(rule: dict[str, object]) -> None:
    _valuespec_inventory_processes_rules().validate_value(
        {**rule, "default_params": {"cpu_rescale_max": True}}, ""
    )


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param({"descr": "%s"}, id="no-match"),
        pytest.param({"descr": "%s", "match_name_or_path": "match_all"}, id="match-all"),
        pytest.param({"descr": "%s", "match_name_or_path": ("match_name", "foo")}, id="exact-name"),
        pytest.param(
            {"descr": "%2", "match_name_or_path": ("match_path", "~(foo)")},
            id="numbered-out-of-range",
        ),
    ],
)
def test_hr_process_discovery_rule_rejects_missing_groups(rule: dict[str, object]) -> None:
    with pytest.raises(MKUserError):
        _valuespec_discovery_hr_processes_rules().validate_value({**rule, "default_params": {}}, "")


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            {"descr": "%s", "match_name_or_path": ("match_name", "~(foo.*)")}, id="one-group"
        ),
        pytest.param(
            {"descr": "%2 %1", "match_name_or_path": ("match_path", "~(a)(b)")},
            id="numbered-groups",
        ),
        pytest.param({"descr": "foo", "match_name_or_path": "match_all"}, id="no-placeholder"),
    ],
)
def test_hr_process_discovery_rule_accepts_matching_groups(rule: dict[str, object]) -> None:
    _valuespec_discovery_hr_processes_rules().validate_value({**rule, "default_params": {}}, "")
