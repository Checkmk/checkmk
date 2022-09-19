#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import nullcontext
from enum import Enum

import pytest

from tests.testlib import on_time

import cmk.gui.valuespec as vs
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html


@pytest.mark.parametrize(
    "args, result",
    [
        ((1546300800, 1, "m"), 1548979200),
        ((1546300800, 3, "m"), 1554076800),
        ((1546300800, -1, "m"), 1543622400),
        ((1546300800, -2, "m"), 1541030400),
        ((1546300800, -3, "m"), 1538352000),
        ((1538352000, 3, "m"), 1546300800),
        ((1546300800, -6, "m"), 1530403200),
    ],
)
def test_timehelper_add(args, result) -> None:  # type:ignore[no-untyped-def]
    with on_time("2019-09-05", "UTC"):
        assert vs.TimeHelper.add(*args) == result


@pytest.mark.parametrize(
    "value, result",
    [
        (-1580000000, "1919-12-07"),
        (1, "1970-01-01"),
        (1580000000, "2020-01-26"),
        (1850000000, "2028-08-16"),
    ],
)
def test_absolutedate_value_to_json_conversion(  # type:ignore[no-untyped-def]
    value, result
) -> None:
    with on_time("2020-03-02", "UTC"):
        assert vs.AbsoluteDate().value_to_html(value) == result
        json_value = vs.AbsoluteDate().value_to_json(value)
        assert vs.AbsoluteDate().value_from_json(json_value) == value


@pytest.mark.parametrize(
    "value, result",
    [
        (120, "2 minutes"),
        (700, "11 minutes 40 seconds"),
        (7580, "2 hours 6 minutes 20 seconds"),
        (527500, "6 days 2 hours 31 minutes 40 seconds"),
    ],
)
def test_age_value_to_json_conversion(value, result) -> None:  # type:ignore[no-untyped-def]
    assert vs.Age().value_to_html(value) == result
    json_value = vs.Age().value_to_json(value)
    assert vs.Age().value_from_json(json_value) == value


@pytest.mark.parametrize(
    "choices, value, result",
    [
        ([(0, "OK"), (1, "WARN"), (2, "CRIT"), (3, "UNKN")], 2, "CRIT"),
        (
            [("h", "Show alerts per hour"), ("d", "Show alerts per day")],
            "h",
            "Show alerts per hour",
        ),
    ],
)
def test_dropdownchoice_value_to_json_conversion(  # type:ignore[no-untyped-def]
    choices, value, result
) -> None:
    assert vs.DropdownChoice(choices=choices).value_to_html(value) == result
    json_value = vs.DropdownChoice(choices=choices).value_to_json(value)
    assert vs.DropdownChoice(choices=choices).value_from_json(json_value) == value


@pytest.mark.parametrize(
    "choices, deprecated_choices, value, is_valid_datatype",
    [
        ([(1, "1"), (2, "2")], [], 1, True),
        ([(1, "1"), (2, "2")], [], 3, True),
        ([(1, "1"), (2, "2")], [None], None, True),
        ([(1, "1"), (2, "2")], ["a"], 4.1523, False),
    ],
    ids=[
        "valid_choice_valid_datatype",
        "invalid_choice_valid_datatype",
        "invalid_choice_valid_deprecated_choice",
        "invalid_choice_invalid_deprecated_choice",
    ],
)
def test_dropdownchoice_validate_datatype(  # type:ignore[no-untyped-def]
    choices, deprecated_choices, value, is_valid_datatype
) -> None:
    dropdown_choice = vs.DropdownChoice[int](
        choices=choices,
        deprecated_choices=deprecated_choices,
    )
    if is_valid_datatype:
        dropdown_choice.validate_datatype(value, "")
    else:
        with pytest.raises(MKUserError):
            dropdown_choice.validate_datatype(value, "")


@pytest.mark.parametrize(
    "value, result_title",
    [
        (("age", 4 * 60 * 60), "The last 4 fun hours"),  # Werk 4477, deprecated input on cmk2.0
        (("age", 25 * 60 * 60), "The last 25 hard hours"),  # Werk 4477, deprecated input on cmk2.0
        (4 * 60 * 60, "The last 4 fun hours"),  # defaults are idents
        (25 * 60 * 60, "The last 25 hard hours"),  # defaults are idents
        (3600 * 24 * 7 * 1.5, "Since a sesquiweek"),  # defaults are idents
    ],
)
def test_timerange_value_to_html_conversion(  # type:ignore[no-untyped-def]
    request_context, monkeypatch, value, result_title
) -> None:
    monkeypatch.setattr(
        active_config,
        "graph_timeranges",
        [
            {"title": "The last 4 fun hours", "duration": 4 * 60 * 60},
            {"title": "The last 25 hard hours", "duration": 25 * 60 * 60},
            {"title": "Since a sesquiweek", "duration": 3600 * 24 * 7 * 1.5},
        ],
    )

    assert vs.Timerange().value_to_html(value) == result_title


def test_timerange_value_to_json_conversion(request_context) -> None:  # type:ignore[no-untyped-def]
    with on_time("2020-03-02", "UTC"):
        for ident, title, _vs in vs.Timerange().choices():
            choice_value: vs.CascadingDropdownChoiceValue = ident
            if ident == "age":
                choice_value = ("age", 12345)
                title = "The last..., 3 hours 25 minutes 45 seconds"
            elif ident == "date":
                choice_value = ("date", (1582671600.0, 1582844400.0))
                title = "Date range, 2020-02-25, 2020-02-27"

            assert vs.Timerange().value_to_html(choice_value) == title
            json_value = vs.Timerange().value_to_json(choice_value)
            assert vs.Timerange().value_from_json(json_value) == choice_value


@pytest.mark.parametrize(
    "address",
    [
        "user@localhost",
        "harri.hirsch@example.com",
        "!#$%&'*+-=?^_`{|}~@c.de",  # other printable ASCII characters
        "user@localhost",
        "harri.hirsch@example.com",
        "!#$%&'*+-=?^_`{|}~@c.de",
        "אሗ@test.de",  # non-ASCII characters
    ],
)
def test_email_validation(address) -> None:  # type:ignore[no-untyped-def]
    vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize(
    "address",
    [
        "a..b@c.de",
        "ab@c..de",
        "a..b@c.de",
        "ab@c..de",
    ],
)
def test_email_validation_non_compliance(address) -> None:  # type:ignore[no-untyped-def]
    # TODO: validate_value should raise an exception in these
    #       cases since subsequent dots without any ASCII
    #       character in between are not allowed in RFC5322.
    vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize(
    "address",
    [
        "text",
        "user@foo",
        "\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
    ],
)
def test_email_validation_raises(address: str) -> None:
    with pytest.raises(MKUserError):
        vs.EmailAddress().validate_value(address, "")


class TestOptional:
    def test_transform_value(self) -> None:
        opt_vs = vs.Optional(
            valuespec=vs.Migrate(
                valuespec=vs.Dictionary(
                    elements=[
                        ("a", vs.TextInput()),
                        ("b", vs.Age()),
                    ]
                ),
                migrate=lambda p: {k: v + 10 if k == "b" else v for k, v in p.items()},
            )
        )
        assert opt_vs.transform_value(None) is None
        assert opt_vs.transform_value({"a": "text", "b": 10}) == {"a": "text", "b": 20}


def test_password_from_html_vars_empty(request_context) -> None:  # type:ignore[no-untyped-def]
    html.request.set_var("pw_orig", "")
    html.request.set_var("pw", "")

    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


def test_password_from_html_vars_not_set(request_context) -> None:  # type:ignore[no-untyped-def]
    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


class ValueType(Enum):
    name = "name"
    ipv4 = "ipv4"
    ipv6 = "ipv6"
    none = "none"


@pytest.mark.parametrize(
    "allow_host_name", (True, False), ids=["allow_host_name", "not allow_host_name"]
)
@pytest.mark.parametrize(
    "allow_ipv4_address", (True, False), ids=["allow_ipv4_address", "not allow_ipv4_address"]
)
@pytest.mark.parametrize(
    "allow_ipv6_address", (True, False), ids=["allow_ipv6_address", "not allow_ipv6_address"]
)
@pytest.mark.parametrize(
    "value_type,value",
    [
        (ValueType.name, "xyz"),
        (ValueType.name, "xyz001_d3"),
        (ValueType.name, "abc-def-ghi"),
        (ValueType.name, "asd.abc"),
        (ValueType.name, "asd.abc."),
        (ValueType.ipv4, "10.10.123.234"),
        (ValueType.ipv4, "10.10.123.234"),
        (ValueType.ipv6, "2001:db8:3333:4444:5555:6666:7777:8888"),
        (ValueType.ipv6, "::1234:5678"),
        (ValueType.none, "999.10.123.234"),
        (ValueType.none, "::&a:5678"),
        (ValueType.none, "/asd/eee"),
        (ValueType.none, "e/d/f"),
        (ValueType.none, "a/../e"),
        (ValueType.none, "-ding"),
        (ValueType.none, "dong-"),
        (ValueType.none, "01234567"),
        (ValueType.none, "012.345.67"),
        (ValueType.none, ""),
    ],
)
def test_host_address_validate_value(
    value_type: ValueType,
    value: str,
    allow_host_name: bool,
    allow_ipv4_address: bool,
    allow_ipv6_address: bool,
) -> None:
    expected_valid = (
        (value_type is ValueType.name and allow_host_name)
        or (value_type is ValueType.ipv4 and allow_ipv4_address)
        or (value_type is ValueType.ipv6 and allow_ipv6_address)
    )
    # mypy is wrong about the nullcontext object type :-(
    with pytest.raises(MKUserError) if not expected_valid else nullcontext():  # type: ignore[attr-defined]
        vs.HostAddress(
            allow_host_name=allow_host_name,
            allow_ipv4_address=allow_ipv4_address,
            allow_ipv6_address=allow_ipv6_address,
            allow_empty=False,
        ).validate_value(value, "varprefix")


@pytest.mark.parametrize(
    "choices,default_value,expected_default",
    [
        (
            [("single_age", "Age", vs.Age(default_value=30))],
            None,
            ("single_age", 30),
        ),
        (
            [("age_1", "Age", vs.Age()), ("age_2", "Age", vs.Age())],
            "age_1",
            ("age_1", 0),
        ),
        (
            [("list_choice", "ListChoice", vs.ListChoice())],
            None,
            ("list_choice", []),
        ),
        ([("value", "Title")], None, "value"),
        ([("value", "Title", None)], None, "value"),
        ([], None, None),
    ],
)
def test_default_value_in_cascading_dropdown(
    choices,
    default_value,
    expected_default,
):
    assert vs.CascadingDropdown(choices=choices).default_value() == expected_default


@pytest.mark.parametrize(
    "choices,default_value,expected_canonical",
    [
        (
            [("single_age", "Age", vs.Age(default_value=30))],
            None,
            ("single_age", 0),
        ),
        (
            [("age_1", "Age", vs.Age()), ("age_2", "Age", vs.Age())],
            "age_1",
            ("age_1", 0),
        ),
        (
            [("list_choice", "ListChoice", vs.ListChoice())],
            None,
            ("list_choice", []),
        ),
        ([], None, None),
        ([("value", "Title")], None, "value"),
        ([("value", "Title", None)], None, "value"),
    ],
)
def test_canonical_value_in_cascading_dropdown(
    choices,
    default_value,
    expected_canonical,
):
    assert vs.CascadingDropdown(choices=choices).canonical_value() == expected_canonical


@pytest.mark.parametrize(
    "valuespec,value,expected",
    [
        (vs.Integer(), 42, 42),
        (
            vs.SSHKeyPair(),
            ("-----BEGIN PRIVATE KEY and so on", "ssh-ed25519 AAAA..."),
            ["******", "ssh-ed25519 AAAA..."],
        ),
        (
            vs.Tuple(
                elements=[
                    vs.TextInput(),
                    vs.Password(),
                    vs.CascadingDropdown(choices=[("password", "_", vs.Password())]),
                ]
            ),
            ("credentials", "hunter2", ("password", "stars")),
            ["credentials", "******", ["password", "******"]],
        ),
    ],
)
def test_mask_to_json(valuespec, value, expected):
    masked = valuespec.mask(value)
    assert valuespec.value_to_json(masked) == expected
