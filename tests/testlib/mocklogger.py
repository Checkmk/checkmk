#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


class MockLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def _log(self, msg: str, args: tuple[object, ...]) -> None:
        self.messages.append(msg % args)

    def info(self, msg: str, *args: object) -> None:
        self._log(msg, args)

    def warning(self, msg: str, *args: object) -> None:
        self._log(msg, args)

    def error(self, msg: str, *args: object) -> None:
        self._log(msg, args)
