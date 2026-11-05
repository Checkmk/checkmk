#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
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


def get_filtered_dict[KT: str, VT_co](
    mapping: Mapping[KT, VT_co], filter_func: Callable[[KT], bool]
) -> Mapping[KT, VT_co]:
    return {k: v for k, v in mapping.items() if filter_func(k)}
