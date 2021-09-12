#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.gui.plugins.openapi.utils import ProblemException


class ProblemKeyError(ProblemException, KeyError):  # pylint: disable=too-many-ancestors
    """Composite Exception representing a ProblemException and a dict KeyError"""


class ParameterDict(dict):
    """A dict where a KeyError is also a Bad Request.

    Examples:

        >>> d = ParameterDict(foo=1, bar=2)

        It's a normal dict:

            >>> d['foo']
            1

        It's a Bad Request:

            >>> try:
            ...     d['baz']
            ... except ProblemKeyError:
            ...     pass

        And the raised Exception is a KeyError as well.

            >>> try:
            ...     d['baz']
            ... except KeyError:
            ...     pass

    """

    def __getitem__(self, key: str) -> Any:
        if key in self:
            rv = super().__getitem__(key)
            if isinstance(rv, dict):
                rv = ParameterDict(rv)
            return rv
        raise ProblemKeyError(400, "Bad request", f"Parameter missing: {key!r}")
