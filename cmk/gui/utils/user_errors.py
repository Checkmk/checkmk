#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Keep track of form and input parameter validation issues during page processing

Errors that appear e.g. while parsing and validating HTTP request parameters before rendering the
actual HTML page may be stored as user errors and displayed later during page rendering on the HTML
page.
"""

from collections.abc import Iterator, Mapping

from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import MKUserError


class UserErrors(Mapping[str | None, str]):
    def __init__(self) -> None:
        self._errors: dict[str | None, str] = {}

    def add(self, error: MKUserError) -> None:
        self._errors[error.varname] = str(error)

    def __bool__(self) -> bool:
        return bool(self._errors)

    def __getitem__(self, key: str | None) -> str:
        return self._errors.__getitem__(key)

    def __iter__(self) -> Iterator[str | None]:
        return self._errors.__iter__()

    def __len__(self) -> int:
        return len(self._errors)


user_errors = request_local_attr("user_errors", UserErrors)
