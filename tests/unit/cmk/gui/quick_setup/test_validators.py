#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import AbstractContextManager as ContextManager
from contextlib import nullcontext as does_not_raise

import pytest

from cmk.gui.form_specs.unstable.validators import HostAddress
from cmk.gui.wato.pages.notifications.quick_setup import (
    validate_notification_count_values,
    validate_throttling_values,
)
from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs.validators import ValidationError


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param((1, 2), id="second value is greater than first"),
        pytest.param((2, 1), id="second value is less than first"),
    ],
)
def test_validate_throttling_values_valid(payload: tuple[int, ...]) -> None:
    validate_throttling_values(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(tuple(), id="no arguments provided"),
        pytest.param((0, 2), id="first value shouldn't be less than 1"),
        pytest.param((1, 0), id="second value shouldn't be less than 1"),
        pytest.param(("foo", 2), id="first value is the wrong type"),
        pytest.param((1, "bar"), id="second value is wrong type"),
        pytest.param((1, 2, 3), id="we only expect two inputs"),
    ],
)
def test_validate_throttling_values_raises(payload: tuple[int, ...]) -> None:
    with pytest.raises(ValidationError):
        validate_throttling_values(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param((1, 2), id="second value is greater than first"),
        pytest.param((1, 1), id="values are the same"),
    ],
)
def test_validate_notification_count_values_valid(payload: tuple[int, ...]) -> None:
    validate_notification_count_values(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(tuple(), id="no arguments provided"),
        pytest.param((0, 1), id="zero is invalid lower bound"),
        pytest.param((0, 0), id="zero is invalid upper bound"),
        pytest.param((2, 1), id="second value less than first"),
        pytest.param(("foo", 2), id="first value is the wrong type"),
        pytest.param((1, "bar"), id="second value is wrong type"),
        pytest.param((1, 2, 3), id="we only expect two inputs"),
    ],
)
def test_validate_notification_count_values_raises(payload: tuple[int, ...]) -> None:
    with pytest.raises(ValidationError):
        validate_notification_count_values(payload)


EXPECTED_HOSTADDRESS_ERROR_MESSAGE = Message("Your input is not a valid hostname or IP address.")


@pytest.mark.parametrize(
    ["test_value", "expected_raises", "expected_message"],
    [
        # Valid IP addressses
        pytest.param("127.0.0.1", does_not_raise(), None, id="IPv4 loopback address"),
        pytest.param("178.26.239.245", does_not_raise(), None, id="valid IPv4"),
        pytest.param("2001:db8::1", does_not_raise(), None, id="valid IPv6 address"),
        pytest.param("::1", does_not_raise(), None, id="IPv6 loopback address"),
        # Invalid IP addresses
        pytest.param(
            "23.75.345.200",
            pytest.raises(ValidationError),
            EXPECTED_HOSTADDRESS_ERROR_MESSAGE,
            id="`The Net` invalid IPv4",
        ),
        # Valid hostnames
        pytest.param("localhost", does_not_raise(), None, id="hostname"),
        pytest.param("example.com", does_not_raise(), None, id="full name address"),
        pytest.param("www.example.com", does_not_raise(), None, id="full name address"),
        pytest.param(
            "very.long.hostname.that.exceeds.the.maximum.allowed.length.and.should.fail.validation.com",
            does_not_raise(),
            None,
            id="long address",
        ),
        pytest.param("123.tld", does_not_raise(), None, id="Contains digits"),
        pytest.param("valid-hostname", does_not_raise(), None, id="Contains hyphen"),
        pytest.param("trailing.dot.", does_not_raise(), None, id="Trailing dot"),
        # Invalid hostnames
        pytest.param(
            "invalid..com",
            pytest.raises(ValidationError),
            EXPECTED_HOSTADDRESS_ERROR_MESSAGE,
            id="Multiple dots",
        ),
        pytest.param(
            "under_score.com",
            pytest.raises(ValidationError),
            EXPECTED_HOSTADDRESS_ERROR_MESSAGE,
            id="Underscore",
        ),
        pytest.param(
            "-starts-with-hyphen.com",
            pytest.raises(ValidationError),
            EXPECTED_HOSTADDRESS_ERROR_MESSAGE,
            id="Starts with hyphen",
        ),
        pytest.param(
            "ends-with-hyphen-.com",
            pytest.raises(ValidationError),
            EXPECTED_HOSTADDRESS_ERROR_MESSAGE,
            id="Ends with hyphen",
        ),
        pytest.param(
            "",
            pytest.raises(ValidationError),
            EXPECTED_HOSTADDRESS_ERROR_MESSAGE,
            id="Empty string",
        ),
        pytest.param(
            ".leading.dot",
            pytest.raises(ValidationError),
            EXPECTED_HOSTADDRESS_ERROR_MESSAGE,
            id="Leading dot",
        ),
    ],
)
def test_host_address(
    test_value: str,
    expected_raises: ContextManager[pytest.ExceptionInfo[ValidationError]],
    expected_message: Message | None,
) -> None:
    with expected_raises as e:
        HostAddress(EXPECTED_HOSTADDRESS_ERROR_MESSAGE)(test_value)

    assert expected_message is None or e.value.message == expected_message
