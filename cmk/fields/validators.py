#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ipaddress
import re

from marshmallow import ValidationError
from marshmallow.validate import Validator


class ValidateIPv4(Validator):
    def __call__(self, value):
        try:
            ipaddress.IPv4Address(value)
        except ValueError as exc:
            raise ValidationError(str(exc))


class ValidateIPv6(Validator):
    """Validate an IPv6 address

    >>> v = ValidateIPv6()
    >>> v("::1")

    >>> v("::0")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    marshmallow.exceptions.ValidationError: This address must never be assigned to any node. ...

    """

    def __init__(
        self,
        allow_unspecified: bool = False,
    ):
        self.allow_unspecified = allow_unspecified

    def __call__(self, value):
        try:
            address = ipaddress.IPv6Address(value)
        except ValueError as exc:
            raise ValidationError(str(exc))

        if not self.allow_unspecified and address.is_unspecified:
            raise ValidationError("This address must never be assigned to any node. [RFC2373]")


class ValidateIPv4Network(Validator):
    """

    Examples:

        >>> validator = ValidateIPv4Network(min_prefix=8, max_prefix=30)
        >>> validator("192.168.0.1/32")
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Prefix of 192.168.0.1/32 must be at most 30 bit

        >>> validator("0.0.0.0/2")
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Prefix of 0.0.0.0/2 must be at least 8 bit

        >>> validator("192.168.0.0/24")

    """

    message_min = "Prefix of {network} must be at least {min} bit"
    message_max = "Prefix of {network} must be at most {max} bit"

    def __init__(self, min_prefix=0, max_prefix=32):
        self.min_prefix = min_prefix
        self.max_prefix = max_prefix

    def __call__(self, value):
        try:
            network = ipaddress.IPv4Network(value)
        except ValueError as exc:
            raise ValidationError(str(exc))

        if network.prefixlen < self.min_prefix:
            raise ValidationError(self.message_min.format(min=self.min_prefix, network=network))

        if network.prefixlen > self.max_prefix:
            raise ValidationError(self.message_max.format(max=self.max_prefix, network=network))


class ValidateAnyOfValidators(Validator):
    """

    Examples:

        >>> from marshmallow.validate import Length
        >>> validator = ValidateAnyOfValidators([Length(min=0, max=4), Length(min=6, max=10)])

        >>> validator("foo")
        >>> validator("barbarbar")

        >>> validator("12345")
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: ['Any of this needs to be true:', \
'Length must be between 0 and 4.', 'Length must be between 6 and 10.']

    """

    def __init__(self, validators):
        self.validators = validators

    def __call__(self, value):
        errors = ["Any of this needs to be true:"]
        for validator in self.validators:
            try:
                validator(value)
                return
            except ValidationError as exc:
                errors.append(str(exc))

        raise ValidationError(errors)


class IsValidRegexp(Validator):
    """

    Examples:

        >>> validator = IsValidRegexp()
        >>> validator("(")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: ...

        >>> validator("()")
        >>> validator("(?:abc())")

    """

    def __call__(self, value):
        try:
            re.compile(value)
        except re.error as exc:
            raise ValidationError(str(exc)) from exc
