#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from typing import Literal


def make_filter_func[CT: str](
    choice: Literal["nothing", "all"] | Sequence[CT],
) -> Callable[[CT], bool]:
    match choice:
        case "nothing":
            return lambda _k: False
        case "all":
            return lambda _k: True
        case _:
            return lambda k: k in choice


def consolidate_filter_funcs[CT: str](
    choices: Sequence[Literal["nothing", "all"] | Sequence[CT]],
) -> Callable[[CT], bool]:
    return lambda kn: any(make_filter_func(c)(kn) for c in choices)


def get_filtered_dict[KT: str, VT_co](
    mapping: Mapping[KT, VT_co], filter_func: Callable[[KT], bool]
) -> Mapping[KT, VT_co]:
    return {k: v for k, v in mapping.items() if filter_func(k)}
