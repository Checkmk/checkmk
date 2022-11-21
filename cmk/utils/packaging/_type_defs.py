#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import re

from cmk.utils.exceptions import MKException


class PackageException(MKException):
    pass


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
