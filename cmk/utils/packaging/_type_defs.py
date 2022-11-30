#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import re
from functools import cached_property

from pydantic import BaseModel

from cmk.utils.exceptions import MKException


class PackageException(MKException):
    pass


class PackageVersion(str):
    # one fine day we might remove the inheritance, but for now this'll have to do.
    _REGEX = re.compile("[0-9.]+")
    _MISMATCH_MSG = "Only digits and dots are allowed in the version number."

    def __new__(cls, value: str) -> PackageVersion:
        if not cls._REGEX.match(value):
            raise ValueError(cls._MISMATCH_MSG)
        return super().__new__(cls, value)

    @cached_property
    def sort_key(self) -> tuple[tuple[float, str], ...]:
        """Try our best to sort version strings

        They should only consist of dots and digits, but we try not to ever crash.
        This does the right thing for reasonable versions:

        >>> PackageVersion("12.3").sort_key()
        ((12, ''), (3, ''))
        >>> PackageVersion("2022.09.03").sort_key() < PackageVersion("2022.8.21").sort_key()
        False

        And it does not crash for nonsense values (which our GUI does not allow).
        Obviously that's not a meaningful result.

        >>> PackageVersion("12.0-alpha").sort_key()
        ((12, ''), (-inf, '0-alpha'))
        >>> PackageVersion("12.0-alpha").sort_key() >= PackageVersion("käsebrot 3.0").sort_key()
        True

        Reasonable ones are "newer":

        >>> PackageVersion("wurstsalat").sort_key() < PackageVersion("0.1").sort_key()
        True
        """
        key_elements: list[tuple[float, str]] = []
        for s in self.split("."):
            try:
                key_elements.append((int(s), ""))
            except ValueError:
                key_elements.append((float("-Inf"), s))

        return tuple(key_elements)


class PackageName(str):
    _REGEX = re.compile(r"^[^\d\W][-\w]*$")
    _MISMATCH_MSG = (
        "A package name must only consist of letters, digits, dash and "
        "underscore and it must start with a letter or underscore."
    )

    def __new__(cls, value: str) -> PackageName:
        if not cls._REGEX.match(value):
            raise ValueError(cls._MISMATCH_MSG)
        return super().__new__(cls, value)


class PackageID(BaseModel, frozen=True):
    name: PackageName
    version: PackageVersion
