#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Protocol


class RRDInterface(Protocol):
    OperationalError: type[Exception]

    def update(self, *args: str) -> None: ...
    def create(self, *args: str) -> None: ...
    def info(self, *args: str) -> Mapping[str, int]: ...
