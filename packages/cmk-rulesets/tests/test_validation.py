#  !/usr/bin/env python3
#  Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Mapping, Sequence
from contextlib import nullcontext as does_not_raise
from typing import ContextManager

import pytest

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.validators import DisallowEmpty, InRange, MatchRegex, ValidationError


@pytest.mark.parametrize(
    ["input_args", "input_message", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param({}, None, 0, does_not_raise(), None, id="no limits specified"),
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
            Localizable("My own message"),
            2.5,
            pytest.raises(ValidationError),
            "My own message",
            id="outside lower limit with custom message",
        ),
        pytest.param(
            {"max_value": 10.0},
            Localizable("My own message"),
            15.0,
            pytest.raises(ValidationError),
            "My own message",
            id="outside upper limit with custom message",
        ),
    ],
)
def test_in_range(
    input_args: Mapping[str, int | float],
    input_message: Localizable | None,
    test_value: int | float,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        InRange(**input_args, error_msg=input_message)(test_value)

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
            {"error_msg": Localizable("My own message")},
            "invalid.string",
            pytest.raises(ValidationError),
            "My own message",
            id="invalid string with custom message",
        ),
    ],
)
def test_match_regex(
    input_regex: str | re.Pattern[str],
    input_msg: Mapping[str, Localizable],
    test_value: str,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        MatchRegex(input_regex, **input_msg)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message


@pytest.mark.parametrize(
    ["input_msg", "test_value", "expected_raises", "expected_message"],
    [
        pytest.param({}, "valid_string", does_not_raise(), None, id="valid string"),
        pytest.param({}, [0, 1, 2], does_not_raise(), None, id="valid sequence"),
        pytest.param(
            {},
            "",
            pytest.raises(ValidationError),
            "An empty value is not allowed here.",
            id="invalid string with default message",
        ),
        pytest.param(
            {},
            [],
            pytest.raises(ValidationError),
            "An empty value is not allowed here.",
            id="invalid sequence with default message",
        ),
        pytest.param(
            {"error_msg": Localizable("My own message")},
            "",
            pytest.raises(ValidationError),
            "My own message",
            id="invalid string with custom message",
        ),
        pytest.param(
            {"error_msg": Localizable("My own message")},
            [],
            pytest.raises(ValidationError),
            "My own message",
            id="invalid sequence with custom message",
        ),
    ],
)
def test_disallow_empty(
    input_msg: Mapping[str, Localizable],
    test_value: str | Sequence[object],
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: str | None,
) -> None:
    with expected_raises as e:
        DisallowEmpty(**input_msg)(test_value)

    assert expected_message is None or e.value.message.localize(lambda x: x) == expected_message
