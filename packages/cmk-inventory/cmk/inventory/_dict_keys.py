#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, kw_only=True)
class DictKeys[T]:
    only_left: set[T]
    both: set[T]
    only_right: set[T]

    @classmethod
    def compare(cls, *, left: set[T], right: set[T]) -> Self:
        return cls(
            only_left=left - right,
            both=left.intersection(right),
            only_right=right - left,
        )
