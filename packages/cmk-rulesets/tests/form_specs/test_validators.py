#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Mapping, Sequence
from contextlib import nullcontext as does_not_raise
from typing import ContextManager

import pytest

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs.validators import (
    EmailAddress,
    LengthInRange,
    MatchRegex,
    NetworkPort,
    NumberInRange,
    RegexGroupsInRange,
    Url,
    UrlProtocol,
    ValidationError,
)


@pytest.mark.parametrize(
    ["input_args", "input_message", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param(
            {},
            None,
            0,
            pytest.raises(ValidationError),
            "Either the minimum or maximum allowed value must be configured, otherwise this "
            "validator is meaningless.",
            id="no limits specified",
        ),
        pytest.param({"min_value": 5.0}, None, 5.0, does_not_raise(), None, id="equal lower limit"),
        pytest.param(
            {"max_value": 50.0}, None, 50.0, does_not_raise(), None, id="equal upper limit"
        ),
        pytest.param(
            {"min_value": 5.0, "max_value": 5.0},
            None,
            5.0,
            does_not_raise(),
            None,
            id="equal both limits",
        ),
        pytest.param(
            {"min_value": 5.0},
            None,
            2.5,
            pytest.raises(ValidationError),
            "The minimum allowed value is 5.0.",
            id="outside lower limit",
        ),
        pytest.param(
            {"max_value": 10.0},
            None,
            15.0,
            pytest.raises(ValidationError),
            "The maximum allowed value is 10.0.",
            id="outside upper limit",
        ),
        pytest.param(
            {
                "min_value": 5.0,
            },
            Message("My own message"),
            2.5,
            pytest.raises(ValidationError),
            "My own message",
            id="outside lower limit with custom message",
        ),
        pytest.param(
            {"max_value": 10.0},
            Message("My own message"),
            15.0,
            pytest.raises(ValidationError),
            "My own message",
            id="outside upper limit with custom message",
        ),
    ],
)
def test_number_in_range(
    input_args: Mapping[str, int | float],
    input_message: Message | None,
    test_value: int | float,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        NumberInRange(**input_args, error_msg=input_message)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message


@pytest.mark.parametrize(
    ["input_args", "input_message", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param(
            {},
            None,
            r"[A-Z]",
            pytest.raises(ValidationError),
            "Either the minimum or maximum number of allowed groups must be configured, otherwise "
            "this validator is meaningless.",
            id="no limits specified",
        ),
        pytest.param(
            {"min_groups": 1}, None, r"(\b[A-Z]+\b)", does_not_raise(), None, id="equal lower limit"
        ),
        pytest.param(
            {"max_groups": 2},
            None,
            r"(\b[A-Z]+\b).+(\b\d+)",
            does_not_raise(),
            None,
            id="equal upper limit",
        ),
        pytest.param(
            {"min_groups": 2, "max_groups": 2},
            None,
            r"(\b[A-Z]+\b).+(\b\d+)",
            does_not_raise(),
            None,
            id="equal both limits",
        ),
        pytest.param(
            {"min_groups": 3},
            None,
            r"(\b[A-Z]+\b).+(\b\d+)",
            pytest.raises(ValidationError),
            "The minimum allowed number of regex groups is 3.",
            id="outside lower limit",
        ),
        pytest.param(
            {"max_groups": 1},
            None,
            r"(\b[A-Z]+\b).+(\b\d+)",
            pytest.raises(ValidationError),
            "The maximum allowed number of regex groups is 1.",
            id="outside upper limit",
        ),
        pytest.param(
            {"min_groups": 1, "max_groups": 3},
            None,
            r"",
            pytest.raises(ValidationError),
            "Allowed number of regex groups ranges from 1 to 3.",
            id="outside both limits",
        ),
        pytest.param(
            {"min_groups": 3},
            Message("My own message"),
            r"(\b[A-Z]+\b).+(\b\d+)",
            pytest.raises(ValidationError),
            "My own message",
            id="outside lower limit with custom message",
        ),
        pytest.param(
            {"max_groups": 1},
            Message("My own message"),
            r"(\b[A-Z]+\b).+(\b\d+)",
            pytest.raises(ValidationError),
            "My own message",
            id="outside upper limit with custom message",
        ),
    ],
)
def test_regex_groups_in_range(
    input_args: Mapping[str, int],
    input_message: Message | None,
    test_value: str,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        RegexGroupsInRange(**input_args, error_msg=input_message)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message


@pytest.mark.parametrize(
    "input_regex",
    [
        pytest.param(r"^[^.\r\n]+$", id="string pattern"),
        pytest.param(re.compile(r"^[^.\r\n]+$"), id="re pattern"),
    ],
)
@pytest.mark.parametrize(
    ["input_msg", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param({}, "valid_string", does_not_raise(), None, id="valid string"),
        pytest.param(
            {},
            "invalid.string",
            pytest.raises(ValidationError),
            r"Your input does not match the required format '^[^.\r\n]+$'.",
            id="invalid string with default message",
        ),
        pytest.param(
            {"error_msg": Message("My own message")},
            "invalid.string",
            pytest.raises(ValidationError),
            "My own message",
            id="invalid string with custom message",
        ),
    ],
)
def test_match_regex(
    input_regex: str | re.Pattern[str],
    input_msg: Mapping[str, Message],
    test_value: str,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        MatchRegex(input_regex, **input_msg)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message


@pytest.mark.parametrize(
    ["input_args", "input_message", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param(
            {"min_value": 1}, None, "valid_string", does_not_raise(), None, id="valid string"
        ),
        pytest.param(
            {"min_value": 1}, None, [0, 1, 2], does_not_raise(), None, id="valid sequence"
        ),
        pytest.param(
            {"min_value": 1},
            None,
            "",
            pytest.raises(ValidationError),
            "The minimum allowed length is 1.",
            id="invalid string with default message (min)",
        ),
        pytest.param(
            {"min_value": 1},
            None,
            [],
            pytest.raises(ValidationError),
            "The minimum allowed length is 1.",
            id="invalid sequence with default message (min)",
        ),
        pytest.param(
            {"max_value": 1},
            None,
            {"a": 1, "b": 2},
            pytest.raises(ValidationError),
            "The maximum allowed length is 1.",
            id="invalid sequence with default message (min)",
        ),
        pytest.param(
            {"min_value": 1},
            Message("My own message"),
            "",
            pytest.raises(ValidationError),
            "My own message",
            id="invalid string with custom message",
        ),
        pytest.param(
            {"min_value": 1},
            Message("My own message"),
            [],
            pytest.raises(ValidationError),
            "My own message",
            id="invalid sequence with custom message",
        ),
    ],
)
def test_length_in_range(
    input_args: Mapping[str, int | float],
    input_message: Message | None,
    test_value: str | Sequence[object],
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        LengthInRange(**input_args, error_msg=input_message)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message


@pytest.mark.parametrize(
    ["input_msg", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param({}, 8001, does_not_raise(), None, id="valid port"),
        pytest.param(
            {},
            65536,
            pytest.raises(ValidationError),
            "Your input does not match the required port range 0-65535.",
            id="invalid port without custom message",
        ),
        pytest.param(
            {},
            -2,
            pytest.raises(ValidationError),
            "Your input does not match the required port range 0-65535.",
            id="invalid port without custom message",
        ),
        pytest.param(
            {"error_msg": Message("My own message")},
            65537,
            pytest.raises(ValidationError),
            "My own message",
            id="invalid port with custom message",
        ),
    ],
)
def test_network_port(
    input_msg: Mapping[str, Message],
    test_value: int,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        NetworkPort(**input_msg)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message


@pytest.mark.parametrize(
    ["protocols", "input_msg", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param(
            [UrlProtocol.FILE], {}, "file://valid/url", does_not_raise(), None, id="valid string"
        ),
        pytest.param(
            [UrlProtocol.HTTP, UrlProtocol.HTTPS],
            {},
            "htp://invalid/url",
            pytest.raises(ValidationError),
            r"Your input is not a valid URL conforming to any allowed protocols ('http, https').",
            id="invalid string with default message",
        ),
        pytest.param(
            [UrlProtocol.SVNSSH],
            {},
            "svnssh://invalid/url",
            pytest.raises(ValidationError),
            r"Your input is not a valid URL conforming to any allowed protocols ('svn+ssh').",
            id="url with invalid scheme",
        ),
        pytest.param(
            [UrlProtocol.MAILTO],
            {},
            "mailto://",
            pytest.raises(ValidationError),
            r"Your input is not a valid URL conforming to any allowed protocols ('mailto').",
            id="url with invalid netloc",
        ),
        pytest.param(
            [UrlProtocol.RSYNC],
            {"error_msg": Message("My own message")},
            "invalid/url",
            pytest.raises(ValidationError),
            "My own message",
            id="url without scheme with custom message",
        ),
    ],
)
def test_url(
    protocols: Sequence[UrlProtocol],
    input_msg: Mapping[str, Message],
    test_value: str,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        Url(protocols, **input_msg)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message


@pytest.mark.parametrize(
    ["input_msg", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param({}, "simple@example.com", does_not_raise(), None, id="valid address"),
        pytest.param(
            {}, "name.surname@example.com", does_not_raise(), None, id="full name address"
        ),
        pytest.param(
            {}, "name.surname@localhost.com", does_not_raise(), None, id="localhost domain"
        ),
        pytest.param(
            {},
            "@example.com",
            pytest.raises(ValidationError),
            "Your input is not a valid email address.",
            id="invalid address without custom message",
        ),
        pytest.param(
            {},
            "name.surname.example.com",
            pytest.raises(ValidationError),
            "Your input is not a valid email address.",
            id="invalid address without @",
        ),
        pytest.param(
            {"error_msg": Message("My own message")},
            "name.surname@example",
            pytest.raises(ValidationError),
            "My own message",
            id="invalid address with custom message",
        ),
    ],
)
def test_email_address(
    input_msg: Mapping[str, Message],
    test_value: str,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        EmailAddress(**input_msg)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message
