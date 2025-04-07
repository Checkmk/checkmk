#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.fields import fields_filter
from cmk.gui.fields.fields_filter import make_filter, parse_fields_filter


@pytest.mark.parametrize(
    "selected_fields, expected_repr",
    [
        ("", "Included"),
        ("(field1)", "Include[field1=Included]"),
        ("(allowed-CHARS_1)", "Include[allowed-CHARS_1=Included]"),
        ("!(field1)", "Exclude[field1=Excluded]"),
        ("(field1,field2)", "Include[field1=Included, field2=Included]"),
        ("!(field1,field2)", "Exclude[field1=Excluded, field2=Excluded]"),
        ("(field1~field2)", "Include[field1=Include[field2=Included]]"),
        ("!(field1~field2)", "Exclude[field1=Exclude[field2=Excluded]]"),
        ("(field1(field2))", "Include[field1=Include[field2=Included]]"),
        ("!(field1(field2))", "Exclude[field1=Exclude[field2=Excluded]]"),
        ("(field1,field1)", "Include[field1=Included]"),
        ("!(field1,field1)", "Exclude[field1=Excluded]"),
        ("(field1,field1~field2)", "Include[field1=Include[field2=Included]]"),
        ("!(field1,field1~field2)", "Exclude[field1=Exclude[field2=Excluded]]"),
        ("(field1,field1(field2))", "Include[field1=Include[field2=Included]]"),
        ("!(field1,field1(field2))", "Exclude[field1=Exclude[field2=Excluded]]"),
        (
            "(field1,field2~field22(field222),field1~field11,field2(field22b))",
            "Include[field1=Include[field11=Included], field2=Include[field22=Include[field222=Included], field22b=Included]]",
        ),
        (
            "!(field1,field2~field22(field222),field1~field11,field2(field22b))",
            "Exclude[field1=Exclude[field11=Excluded], field2=Exclude[field22=Exclude[field222=Excluded], field22b=Excluded]]",
        ),
    ],
)
def test_parse_selected_fields(selected_fields: str, expected_repr: str) -> None:
    parsed = parse_fields_filter(selected_fields)
    assert repr(parsed) == expected_repr


def test_parse_selected_fields_sorted() -> None:
    include = parse_fields_filter("(field2,field1)")
    exclude = parse_fields_filter("!(field2,field1)")
    assert repr(include) == "Include[field1=Included, field2=Included]"
    assert repr(exclude) == "Exclude[field1=Excluded, field2=Excluded]"


@pytest.mark.parametrize(
    "selected_fields",
    [
        # missing parenthesis
        "field1",
        "!field1",
        "(field1",
        "!(field1",
        "field1)",
        "!field1)",
        # trailing comma
        "field1,",
        "!field1,",
        "(field1,)",
        # invalid characters
        "(invalid.name)",
        "(invalid/name)",
        "(invalid\\name)",
        "(invalid[name])",
    ],
)
def test_parse_selected_fields_invalid(selected_fields: str) -> None:
    with pytest.raises(ValueError):
        parse_fields_filter(selected_fields)


def test_apply_include_filter() -> None:
    include = parse_fields_filter("(field1,field2(field22))")
    assert include.apply({"field1": 1, "field2": {"field21": 21, "field22": 22}, "field3": 3}) == {
        "field1": 1,
        "field2": {"field22": 22},
    }
    assert include.apply({"field1": {"field2": {"field21": 21, "field22": 22}, "field3": 3}}) == {
        "field1": {"field2": {"field21": 21, "field22": 22}, "field3": 3}
    }
    assert include.apply(
        [{"field1": 1, "field2": {"field21": 21, "field22": 22}, "field3": 3}, {"field4": 4}]
    ) == [{"field1": 1, "field2": {"field22": 22}}, {}]


def test_apply_exclude_filter() -> None:
    exclude = parse_fields_filter("!(field1,field2(field22))")
    assert exclude.apply({"field1": 1, "field2": {"field21": 21, "field22": 22}, "field3": 3}) == {
        "field2": {"field21": 21},
        "field3": 3,
    }
    assert exclude.apply({"field1": {"field2": {"field21": 21, "field22": 22}, "field3": 3}}) == {}
    assert exclude.apply(
        [{"field1": 1, "field2": {"field21": 21, "field22": 22}, "field3": 3}, {"field4": 4}]
    ) == [{"field2": {"field21": 21}, "field3": 3}, {"field4": 4}]


def test_get_nested_fields_include_filter() -> None:
    include = parse_fields_filter("(field1,field2(field22))")
    assert include.get_nested_fields("field1") == make_filter(this_is="included")
    assert include.get_nested_fields("field2") == parse_fields_filter("(field22)")
    assert include.get_nested_fields("field3") == make_filter(this_is="excluded")


def test_get_nested_fields_exclude_filter() -> None:
    exclude = parse_fields_filter("!(field1,field2(field22))")
    assert exclude.get_nested_fields("field1") == make_filter(this_is="excluded")
    assert exclude.get_nested_fields("field2") == parse_fields_filter("!(field22)")
    assert exclude.get_nested_fields("field3") == make_filter(this_is="included")


def test_make_filter_empty_raises() -> None:
    with pytest.raises(ValueError):
        make_filter()


def test_make_filter_multiple_args_raises() -> None:
    with pytest.raises(ValueError):
        make_filter(include={}, exclude={})

    with pytest.raises(ValueError):
        make_filter(include={}, this_is="included")

    with pytest.raises(ValueError):
        make_filter(exclude={}, this_is="excluded")


def test_make_filter_mixed_raises() -> None:
    include_filter = make_filter(this_is="included")
    with pytest.raises(ValueError):
        make_filter(exclude={"field": include_filter})

    exclude_filter = make_filter(this_is="excluded")
    with pytest.raises(ValueError):
        make_filter(include={"field": exclude_filter})


def test_make_filter_empty_dict_raises() -> None:
    with pytest.raises(ValueError):
        make_filter(include={})

    with pytest.raises(ValueError):
        make_filter(exclude={})


def test_make_filter() -> None:
    assert isinstance(make_filter(this_is="included"), fields_filter._Included)
    assert isinstance(make_filter(this_is="excluded"), fields_filter._Excluded)

    include_filter = make_filter(include={"field": make_filter(this_is="included")})
    assert isinstance(include_filter, fields_filter._IncludeFields)
    assert repr(include_filter) == repr(parse_fields_filter("(field)"))

    exclude_filter = make_filter(exclude={"field": make_filter(this_is="excluded")})
    assert isinstance(exclude_filter, fields_filter._ExcludeFields)
    assert repr(exclude_filter) == repr(parse_fields_filter("!(field)"))
