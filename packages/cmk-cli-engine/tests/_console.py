#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import signal
from collections.abc import Mapping, Sequence
from typing import override


class FakeTerminal(io.StringIO):
    """Stands in for an output stream, on a terminal or redirected"""

    def __init__(self, *, tty: bool = False) -> None:
        super().__init__()
        self._tty = tty

    @override
    def isatty(self) -> bool:
        return self._tty


class FakeRunPager:
    """Stands in for running the pager: records what it was asked to show, and how"""

    def __init__(self, error: Exception | None = None) -> None:
        self.commands: list[Sequence[str]] = []
        self.texts: list[str] = []
        self.environments: list[Mapping[str, str]] = []
        self.sigint_handlers: list[object] = []
        self._error = error

    def __call__(self, command: Sequence[str], txt: str, environ: Mapping[str, str]) -> None:
        self.commands.append(command)
        self.texts.append(txt)
        self.environments.append(environ)
        self.sigint_handlers.append(signal.getsignal(signal.SIGINT))
        if self._error is not None:
            raise self._error
