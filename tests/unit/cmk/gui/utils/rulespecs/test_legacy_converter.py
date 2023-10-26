#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from functools import partial

import pytest

import cmk.gui.valuespec as legacy_valuespecs
import cmk.gui.watolib.rulespecs as legacy_rulespecs
from cmk.gui import wato, watolib
from cmk.gui.i18n import _
from cmk.gui.utils.rulespecs.legacy_converter import (
    _convert_to_legacy_rulespec_group,
    _convert_to_legacy_valuespec,
    convert_to_legacy_rulespec,
)

import cmk.rulesets.v1 as api_v1


@pytest.mark.parametrize(
    ["new_valuespec", "expected"],
    [
        pytest.param(
            api_v1.MonitoringState(
                title=api_v1.Localizable("title"), default_value=api_v1.State.OK
            ),
            legacy_valuespecs.MonitoringState(title=_("title"), default_value=0),
            id="MonitoringState",
        ),
        pytest.param(
            api_v1.Dictionary(elements={}),
            legacy_valuespecs.Dictionary(elements=[]),
            id="minimal Dictionary",
        ),
        pytest.param(
            api_v1.Dictionary(
                elements={
                    "key_req": api_v1.DictElement(
                        api_v1.MonitoringState(title=api_v1.Localizable("title")),
                        required=True,
                    ),
                    "key_opt": api_v1.DictElement(
                        api_v1.MonitoringState(title=api_v1.Localizable("title")),
                        show_more=True,
                    ),
                    "key_ignored": api_v1.DictElement(
                        api_v1.MonitoringState(title=api_v1.Localizable("title")),
                        ignored=True,
                    ),
                },
                title=api_v1.Localizable("Configuration title"),
                help_text=api_v1.Localizable("Helpful description"),
                no_elements_text=api_v1.Localizable("No elements specified"),
            ),
            legacy_valuespecs.Dictionary(
                elements=[
                    ("key_req", legacy_valuespecs.MonitoringState(title=_("title"))),
                    ("key_opt", legacy_valuespecs.MonitoringState(title=_("title"))),
                    ("key_ignored", legacy_valuespecs.MonitoringState(title=_("title"))),
                ],
                title=_("Configuration title"),
                help=_("Helpful description"),
                empty_text=_("No elements specified"),
                required_keys=["key_req"],
                default_keys=["key_req"],
                show_more_keys=["key_opt"],
                ignored_keys=["key_ignored"],
            ),
            id="Dictionary",
        ),
    ],
)
def test_convert_to_legacy_valuespec(
    new_valuespec: api_v1.ValueSpec, expected: legacy_valuespecs.ValueSpec
) -> None:
    _compare_specs(_convert_to_legacy_valuespec(new_valuespec, _), expected)


@pytest.mark.parametrize(
    ["new_group", "expected"],
    [
        pytest.param(
            api_v1.RuleSpecSubGroup.CHECK_PARAMETERS_APPLICATIONS,
            wato.RulespecGroupCheckParametersApplications,
            id="CheckParametersApplications",
        )
    ],
)
def test_convert_to_legacy_rulespec_group(
    new_group: api_v1.RuleSpecSubGroup, expected: type[watolib.rulespecs.RulespecSubGroup]
) -> None:
    assert _convert_to_legacy_rulespec_group(new_group) == expected


@pytest.mark.parametrize(
    ["new_rulespec", "expected"],
    [
        pytest.param(
            api_v1.CheckParameterRuleSpecWithItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                group=api_v1.RuleSpecSubGroup.CHECK_PARAMETERS_APPLICATIONS,
                item=api_v1.TextInput(title=api_v1.Localizable("item title")),
                value_spec=partial(
                    api_v1.Dictionary,
                    elements={
                        "key": api_v1.DictElement(
                            api_v1.MonitoringState(title=api_v1.Localizable("valuespec title"))
                        ),
                    },
                ),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.CheckParameterRulespecWithItem(
                check_group_name="test_rulespec",
                group=wato.RulespecGroupCheckParametersApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(title=_("item title")),
                parameter_valuespec=lambda: legacy_valuespecs.Dictionary(
                    elements=[
                        ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                    ],
                ),
                match_type="dict",
                create_manual_check=False,  # TODO adapt when enforced services are created
            ),
            id="CheckParameterRuleSpecWithItem",
        )
    ],
)
def test_convert_to_legacy_rulespec(
    new_rulespec: api_v1.RuleSpec, expected: legacy_rulespecs.Rulespec
) -> None:
    _compare_specs(convert_to_legacy_rulespec(new_rulespec, _), expected)


def _compare_specs(actual: object, expected: object) -> None:
    if isinstance(expected, Iterable) and not isinstance(expected, str):
        assert isinstance(actual, Iterable) and not isinstance(actual, str)
        for actual_elem, expected_elem in zip(actual, expected):
            _compare_specs(actual_elem, expected_elem)
        return

    if not hasattr(expected, "__dict__"):
        assert actual == expected
        return

    assert expected.__dict__.keys() == actual.__dict__.keys()
    for attr, expected_value in expected.__dict__.items():
        actual_value = getattr(actual, attr)
        if not callable(expected_value):
            _compare_specs(actual_value, expected_value)
            continue

        try:
            _compare_specs(actual_value(), expected_value())
        except TypeError:  # deal with valuespec constructors
            assert actual_value == expected_value
