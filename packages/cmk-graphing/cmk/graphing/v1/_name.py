#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass


@dataclass(frozen=True)
class Name:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError(self.value)
