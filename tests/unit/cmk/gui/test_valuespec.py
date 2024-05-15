#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from binascii import unhexlify
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.gui.valuespec as vs
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request


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
def test_timehelper_add(args: tuple[int, int, str], result: int) -> None:
    with time_machine.travel(datetime.datetime(2019, 9, 5, tzinfo=ZoneInfo("UTC"))):
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
def test_absolutedate_value_to_json_conversion(value: int, result: str) -> None:
    with time_machine.travel(datetime.datetime(2020, 3, 2, tzinfo=ZoneInfo("UTC"))):
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
def test_age_value_to_json_conversion(value: int, result: str) -> None:
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
def test_dropdownchoice_value_to_json_conversion(
    choices: vs.DropdownChoices, value: object, result: vs.ValueSpecText
) -> None:
    assert vs.DropdownChoice[object](choices=choices).value_to_html(value) == result
    json_value = vs.DropdownChoice[object](choices=choices).value_to_json(value)
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
    choices: vs.DropdownChoices,
    deprecated_choices: Sequence[str | None],
    value: int | None,
    is_valid_datatype: bool,
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


@pytest.mark.usefixtures("request_context")
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
    monkeypatch: pytest.MonkeyPatch,
    value: vs.CascadingDropdownChoiceValue,
    result_title: vs.ValueSpecText,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "graph_timeranges",
            [
                {"title": "The last 4 fun hours", "duration": 4 * 60 * 60},
                {"title": "The last 25 hard hours", "duration": 25 * 60 * 60},
                {"title": "Since a sesquiweek", "duration": 3600 * 24 * 7 * 1.5},
            ],
        )

        assert vs.Timerange().value_to_html(value) == result_title


@pytest.mark.usefixtures("request_context")
def test_timerange_value_to_json_conversion() -> None:
    with time_machine.travel(datetime.datetime(2020, 3, 2, tzinfo=ZoneInfo("UTC"))):
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
def test_email_validation(address: str) -> None:
    vs.EmailAddress().validate_value(address, "")


def _example_image_data():
    """A tiny but valid PNG image"""
    return unhexlify(
        b"89504e470d0a1a0a0000000d494844520000000100"
        b"0000010802000000907753de000000037342495408"
        b"0808dbe14fe00000000c49444154089963b876f51a"
        b"0005060282db61224c0000000049454e44ae426082"
    )


@pytest.mark.parametrize(
    "filedata",
    [
        # Should raise is when trying to be opened
        ("file.png", "image/png", b"\x89PNG"),
        ("OneByOne.png", "image/jpeg", _example_image_data()),
        ("OneByOne.jpg", "image/png", _example_image_data()),
        ("OneByOne.png.jpg", "image/png", _example_image_data()),
        ("OneByOne.png", "!image/png", _example_image_data()),
        ("OneByOne.png", "image/pngA", _example_image_data()),
        ("OneByOne.png%20", "image/png", _example_image_data()),
    ],
)
def test_imageupload_non_compliance(filedata: vs.FileUploadModel) -> None:
    with pytest.raises(MKUserError):
        vs.ImageUpload(mime_types=["image/png"]).validate_value(filedata, "prefix")


@pytest.mark.parametrize("filedata", [("OneByOne.png", "image/png", _example_image_data())])
def test_imageupload_compliance(filedata: vs.FileUploadModel) -> None:
    vs.ImageUpload(mime_types=["image/png"]).validate_value(filedata, "prefix")


@pytest.mark.parametrize(
    "address",
    [
        "a..b@c.de",
        "ab@c..de",
        "a..b@c.de",
        "ab@c..de",
    ],
)
def test_email_validation_non_compliance(address: str) -> None:
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


@pytest.mark.usefixtures("request_context")
def test_password_from_html_vars_empty() -> None:
    request.set_var("pw_orig", "")
    request.set_var("pw", "")

    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


@pytest.mark.usefixtures("request_context")
def test_password_from_html_vars_not_set() -> None:
    pw = vs.Password()
    assert pw.from_html_vars("pw") == ""


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


class TestAlternative:
    def test_transform_value_ok(self) -> None:
        assert (
            vs.Alternative(
                elements=[
                    vs.Transform(
                        vs.Integer(),
                        to_valuespec=lambda v: v + 1,
                        from_valuespec=lambda v: v,
                    )
                ]
            ).transform_value(3)
            == 3 + 1
        )

    def test_transform_value_no_match(self) -> None:
        with pytest.raises(MKUserError):
            vs.Alternative(
                elements=[
                    vs.Integer(),
                ]
            ).transform_value("strange")


@pytest.mark.parametrize(
    "hostname",
    (
        "",  # empty
        "../../foo",  # invalid char, path traversal
        "a" * 255,  # too long
    ),
)
def test_nvalid_hostnames_rejected(hostname: str) -> None:
    """test that certain hostnames fail validation"""

    with pytest.raises(MKUserError):
        vs.Hostname().validate_value(hostname, "varprefix")
