#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import hashlib
from contextlib import nullcontext
from enum import Enum

import pytest

from tests.testlib import on_time

import cmk.utils.paths
from cmk.utils.encryption import Encrypter

import cmk.gui.valuespec as vs
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html


@pytest.mark.parametrize(
    "entry, result",
    [
        ("m0", ((1567296000, 1567702200), "September 2019")),
        ("m1", ((1564617600, 1567296000), "August 2019")),
        ("m3", ((1559347200, 1567296000), "June 2019 — August 2019")),
        ("y1", ((1514764800, 1546300800), "2018")),
        ("y0", ((1546300800, 1567702200), "2019")),
        ("4h", ((1567687800, 1567702200), "Last 4 hours")),
        (4 * 60 * 60, ((1567687800, 1567702200), "The last 4 hours")),
        ("25h", ((1567612200, 1567702200), "Last 25 hours")),
        ("8d", ((1567011000, 1567702200), "Last 8 days")),
        ("15d", ((1566406200, 1567702200), "Last 15 days")),
        ("35d", ((1564678200, 1567702200), "Last 35 days")),
        ("400d", ((1533142200, 1567702200), "Last 400 days")),
        ("d0", ((1567641600, 1567702200), "Today")),
        ("d1", ((1567555200, 1567641600), "Yesterday")),
        ("d7", ((1567036800, 1567123200), "2019-08-29")),
        ("d8", ((1566950400, 1567036800), "2019-08-28")),
        ("w0", ((1567382400, 1567702200), "This week")),
        ("w1", ((1566777600, 1567382400), "Last week")),
        ("w2", ((1566172800, 1566777600), "2019-08-19 — 2019-08-25")),
        (("date", (1536098400, 1567288800)), ((1536098400, 1567375200), "2018-09-04 — 2019-09-01")),
        (("until", 1577232000), ((1567702200, 1577232000), "2019-12-25")),
        (("time", (1549374782, 1567687982)), ((1549374782, 1567687982), "2019-02-05 — 2019-09-05")),
        (("age", 2 * 3600), ((1567695000, 1567702200), "The last 2 hours")),
        (("next", 3 * 3600), ((1567702200, 1567713000), "The next 3 hours")),
    ],
)
def test_timerange(entry, result) -> None:
    with on_time("2019-09-05 16:50", "UTC"):
        assert vs.Timerange.compute_range(entry) == vs.ComputedTimerange(*result)


@pytest.mark.parametrize(
    "entry, refutcdate, result",
    [
        ("m0", "2019-09-15 15:09", ((1567296000, 1568560140), "September 2019")),
        ("m1", "2019-01-12", ((1543622400, 1546300800), "December 2018")),
        ("m-1", "2019-09-15 15:09", ((1567296000, 1569888000), "September 2019")),
        ("m2", "2019-02-12", ((1543622400, 1548979200), "December 2018 — January 2019")),
        ("m3", "2019-02-12", ((1541030400, 1548979200), "November 2018 — January 2019")),
        ("m-3", "2019-02-12", ((1548979200, 1556668800), "February 2019 — April 2019")),
        ("m-3", "2018-12-12", ((1543622400, 1551398400), "December 2018 — February 2019")),
        ("m6", "2019-02-12", ((1533081600, 1548979200), "August 2018 — January 2019")),
        ("m-6", "2019-02-12", ((1548979200, 1564617600), "February 2019 — July 2019")),
        ("y0", "2019-09-15", ((1546300800, 1568505600), "2019")),
        ("y1", "2019-09-15", ((1514764800, 1546300800), "2018")),
        ("y-1", "2019-09-15", ((1546300800, 1577836800), "2019")),
        ("f0", "2020-01-25", ((1577836800, 1577923200), "01/01/2020")),
        ("f1", "2020-01-25", ((1575158400, 1575244800), "01/12/2019")),
        ("l1", "2020-01-25", ((1577750400, 1577836800), "31/12/2019")),
        ("l1", "2020-03-25", ((1582934400, 1583020800), "29/02/2020")),
    ],
)
def test_timerange2(entry, refutcdate, result) -> None:
    with on_time(refutcdate, "UTC"):
        assert vs.Timerange.compute_range(entry) == vs.ComputedTimerange(*result)


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
def test_timehelper_add(args, result) -> None:
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
def test_absolutedate_value_to_json_conversion(value, result) -> None:
    with on_time("2020-03-02", "UTC"):
        assert vs.AbsoluteDate().value_to_html(value) == result
        json_value = vs.AbsoluteDate().value_to_json(value)
        assert vs.AbsoluteDate().value_from_json(json_value) == value


@pytest.mark.parametrize(
    "value, result",
    [
        ((1582671600, 1582844400), "2020-02-25, 2020-02-27"),
        ((1577833200, 1580425200), "2019-12-31, 2020-01-30"),
    ],
)
def test_tuple_value_to_json_conversion(value, result) -> None:
    with on_time("2020-03-02", "UTC"):
        assert (
            vs.Tuple(elements=[vs.AbsoluteDate(), vs.AbsoluteDate()]).value_to_html(value) == result
        )
        json_value = vs.Tuple(elements=[vs.AbsoluteDate(), vs.AbsoluteDate()]).value_to_json(value)
        assert (
            vs.Tuple(elements=[vs.AbsoluteDate(), vs.AbsoluteDate()]).value_from_json(json_value)
            == value
        )


@pytest.mark.parametrize(
    "value, result",
    [
        (120, "2 minutes"),
        (700, "11 minutes 40 seconds"),
        (7580, "2 hours 6 minutes 20 seconds"),
        (527500, "6 days 2 hours 31 minutes 40 seconds"),
    ],
)
def test_age_value_to_json_conversion(value, result) -> None:
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
def test_dropdownchoice_value_to_json_conversion(choices, value, result) -> None:
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
def test_dropdownchoice_validate_datatype(
    choices, deprecated_choices, value, is_valid_datatype
) -> None:
    dropdown_choice = vs.DropdownChoice(
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
def test_timerange_value_to_html_conversion(
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


def test_timerange_value_to_json_conversion(request_context) -> None:
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
    "elements,value,expected",
    [
        ([], {}, {}),
        ([], {"a": 1}, {}),
        ([("a", vs.Integer())], {"a": 1}, {"a": 1}),
        ([("a", vs.Tuple(elements=[]))], {"a": tuple()}, {"a": []}),
    ],
)
def test_dictionary_value_to_json(elements, value, expected) -> None:
    assert vs.Dictionary(elements=elements).value_to_json(value) == expected


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
def test_email_validation(address) -> None:
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
def test_email_validation_non_compliance(address) -> None:
    # TODO: validate_value should raise an exception in these
    #       cases since subsequent dots without any ASCII
    #       character in between are not allowed in RFC5322.
    vs.EmailAddress().validate_value(address, "")


@pytest.mark.parametrize(
    "address",
    [
        b"text",
        b"user@foo",
        b"\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
        "אሗ@test.com".encode("utf-8"),  # UTF-8 encoded bytestrings are not allowed
        "text",
        "user@foo",
        "\t\n a@localhost \t\n",  # whitespace is removed in from_html_vars
    ],
)
def test_email_validation_raises(address) -> None:
    with pytest.raises(MKUserError):
        vs.EmailAddress().validate_value(address, "")


def test_transform_value_no_transform_vs() -> None:
    valuespec = vs.TextInput()
    assert valuespec.transform_value("lala") == "lala"
    assert valuespec.transform_value("AAA") == "AAA"


def test_transform_value_with_transform_vs() -> None:
    valuespec = vs.Transform(
        valuespec=vs.TextInput(),
        forth=lambda x: x if x == "lala" else x.upper(),
        back=lambda x: x + "aaa",
    )

    assert valuespec.transform_value("lala") == "lalaaaa"
    assert valuespec.transform_value("AAA") == "AAAaaa"


def test_transform_value_dict() -> None:
    valuespec = vs.Dictionary(
        elements=[
            ("a", vs.TextInput()),
        ]
    )
    assert valuespec.transform_value({"a": "lala"}) == {"a": "lala"}


def test_transform_value_in_dict() -> None:
    valuespec = vs.Dictionary(
        elements=[
            (
                "a",
                vs.Transform(
                    valuespec=vs.TextInput(),
                    forth=lambda x: x if x == "lala" else x.upper(),
                    back=lambda x: x + "aaa",
                ),
            ),
        ]
    )

    assert valuespec.transform_value({"a": "lala"}) == {"a": "lalaaaa"}
    assert valuespec.transform_value({"a": "AAA"}) == {"a": "AAAaaa"}


def test_transform_value_in_tuple() -> None:
    valuespec = vs.Tuple(
        elements=[
            vs.Transform(
                valuespec=vs.TextInput(),
                forth=lambda x: x if x == "lala" else x.upper(),
                back=lambda x: x + "aaa",
            ),
            vs.Transform(
                valuespec=vs.TextInput(),
                forth=lambda x: x if x == "lala" else x.upper(),
                back=lambda x: x + "aaa",
            ),
        ]
    )

    assert valuespec.transform_value(("lala", "AAA")) == ("lalaaaa", "AAAaaa")


def test_transform_value_in_cascading_dropdown() -> None:
    valuespec = vs.CascadingDropdown(
        choices=[
            ("a", "Title a", vs.TextInput()),
            (
                "b",
                "Title b",
                vs.Transform(
                    valuespec=vs.TextInput(),
                    forth=lambda x: x if x == "lala" else x.upper(),
                    back=lambda x: x + "aaa",
                ),
            ),
        ]
    )

    assert valuespec.transform_value(("a", "abc")) == ("a", "abc")
    assert valuespec.transform_value(("b", "lala")) == ("b", "lalaaaa")
    assert valuespec.transform_value(("b", "AAA")) == ("b", "AAAaaa")


def test_transform_value_and_json() -> None:
    # before all keys where upper case, then we decided to move to lower case,
    # but want to keep compatibility with old values saved in the config
    valuespec = vs.Transform(
        valuespec=vs.Dictionary(
            elements=[
                ("key1", vs.TextInput()),
            ]
        ),
        forth=lambda x: {k.lower(): v for k, v in x.items()},
    )
    assert valuespec.transform_value({"KEY1": "value1"}) == {"key1": "value1"}

    assert valuespec.value_to_json({"KEY1": "value1"}) == {"key1": "value1"}
    assert valuespec.value_from_json({"key1": "value1"}) == {"key1": "value1"}


class TestOptional:
    def test_transform_value(self) -> None:
        opt_vs = vs.Optional(
            valuespec=vs.Transform(
                valuespec=vs.Dictionary(
                    elements=[
                        ("a", vs.TextInput()),
                        ("b", vs.Age()),
                    ]
                ),
                forth=lambda p: {k: v + 10 if k == "b" else v for k, v in p.items()},
            )
        )
        assert opt_vs.transform_value(None) is None
        assert opt_vs.transform_value({"a": "text", "b": 10}) == {"a": "text", "b": 20}


@pytest.fixture()
def fixture_auth_secret():
    secret_path = cmk.utils.paths.omd_root / "etc" / "auth.secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    with secret_path.open("wb") as f:
        f.write(b"auth-secret")


def test_password_from_html_vars_empty(request_context) -> None:
    html.request.set_var("pw_orig", "")
    html.request.set_var("pw", "")

    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


def test_password_from_html_vars_not_set(request_context) -> None:
    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


@pytest.mark.usefixtures("fixture_auth_secret")
def test_password_from_html_vars_initial_pw(request_context) -> None:
    html.request.set_var("pw_orig", "")
    html.request.set_var("pw", "abc")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "abc"


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
@pytest.mark.usefixtures("fixture_auth_secret")
def test_password_from_html_vars_unchanged_pw(request_context) -> None:
    html.request.set_var("pw_orig", base64.b64encode(Encrypter.encrypt("abc")).decode("ascii"))
    html.request.set_var("pw", "")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "abc"


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
@pytest.mark.usefixtures("fixture_auth_secret")
def test_password_from_html_vars_change_pw(request_context) -> None:
    html.request.set_var("pw_orig", base64.b64encode(Encrypter.encrypt("abc")).decode("ascii"))
    html.request.set_var("pw", "xyz")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "xyz"


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
