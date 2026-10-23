# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override


class DevServerError(Exception):
    """The dev server cannot be built, started or watched."""

    def __init__(self, message: str, recovery: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.recovery = recovery

    @override
    def __str__(self) -> str:
        return f"{self.message}\n{self.recovery}" if self.recovery else self.message
