#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Exceptions a self-rendering feature page may raise.

``cmk.gui`` translates these into its own HTTP-aware exceptions when composing
the page, so a feature stays free of a ``cmk.gui`` dependency.
"""

from typing import override


class MKUserError(Exception):
    """Raised to signal a user-facing input error.

    ``cmk.gui`` renders this as a friendly error message bound to ``varname``.
    """

    def __init__(self, varname: str | None, message: str) -> None:
        super().__init__(message)
        self.varname = varname
        self.message = message

    @override
    def __str__(self) -> str:
        return self.message


class MKNotFound(Exception):
    """Raised to signal that the requested resource does not exist.

    ``cmk.gui`` renders this as its 404 page.
    """
