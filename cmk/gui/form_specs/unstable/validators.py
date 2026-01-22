#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ipaddress
import re
import typing

from cmk.rulesets.v1._localize import Message
from cmk.rulesets.v1.form_specs.validators import LengthInRange, ValidationError

T = typing.TypeVar("T")

ModelT = typing.TypeVar("ModelT")

ValidatorType = typing.Callable[[ModelT], None]


class EnforceSuffix:
    def __init__(
        self,
        suffix: str,
        *,
        case: typing.Literal["ignore", "sensitive"],
        error_msg: Message = Message("Does not end with %s"),
    ) -> None:
        self.suffix = suffix
        self.case = case
        self.error_msg = error_msg

    def __call__(self, value: str) -> None:
        if self.case == "ignore":
            to_check = value.lower()
            suffix = self.suffix.lower()
        else:
            to_check = value
            suffix = self.suffix

        if not to_check.endswith(suffix):
            raise ValidationError(self.error_msg % suffix)


class IsInteger:
    def __init__(
        self,
        error_msg: Message = Message("Number is not an integer value."),
    ) -> None:
        self.error_msg = error_msg

    def __call__(self, value: typing.Any) -> None:
        if not isinstance(value, int):
            raise ValidationError(self.error_msg)


class IsFloat:
    def __init__(
        self,
        error_msg: Message = Message("Number is not a float value."),
    ) -> None:
        self.error_msg = error_msg

    def __call__(self, value: typing.Any) -> None:
        if not isinstance(value, float | int):
            raise ValidationError(self.error_msg)


def not_empty(error_msg: Message | None = None) -> LengthInRange:
    return LengthInRange(
        min_value=1,
        error_msg=error_msg
        if error_msg is not None
        else Message("An empty value is not allowed here"),
    )


class HostAddress:
    """Validator that ensures the validated value is a hostname or IP address.

    It does not resolve the hostname or check if the IP address is reachable.
    """

    def __init__(
        self,
        error_msg: Message = Message("Your input is not a valid hostname or IP address."),
    ) -> None:
        self.error_msg = error_msg

    def _validate_ipaddress(self, value: str) -> None:
        ipaddress.ip_address(value)

    def _validate_hostname(self, value: str) -> None:
        total_length = len(value)
        if value.endswith("."):
            value = value[:-1]
            total_length -= 1

        if total_length > 253:
            raise ValidationError(self.error_msg)

        labels = value.split(".")

        if any(len(label) > 63 for label in labels):
            raise ValidationError(self.error_msg)

        pattern = r"(?!-)[a-z0-9-]{1,63}(?<!-)$"
        allowed = re.compile(pattern, re.IGNORECASE)

        # TLD must not be all numeric
        if re.match(r"[0-9]+$", labels[-1]):
            raise ValidationError(self.error_msg)

        # Check each label
        for label in labels:
            if (not label) or (not allowed.match(label)):
                raise ValidationError(self.error_msg)

    def __call__(self, value: str) -> None:
        if not value:
            raise ValidationError(self.error_msg)

        try:
            self._validate_ipaddress(value)
            return
        except ValueError:
            pass

        self._validate_hostname(value)


class HostAddressList:
    """Validator that ensures all values in a list are valid hostnames or IP addresses."""

    def __init__(self) -> None:
        self._validator = HostAddress()

    def __call__(self, value: typing.Sequence[str]) -> None:
        for hostname in value:
            if hostname:
                self._validator(hostname)
