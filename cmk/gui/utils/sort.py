#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, List

from cmk.gui.num_split import key_num_split


def _make_key(key: str) -> tuple[int | str, ...]:
    is_symbol = not key[0].isalnum()
    is_number = key[0].isdigit()
    split = key_num_split(key.casefold())

    order = (
        (not is_number and is_symbol) * 1
        + (is_number and not is_symbol) * 2
        + (not is_number and not is_symbol) * 3
    )
    return (order, *split)


def natural_sort(items: Iterable[str], reverse: bool = False) -> List[str]:
    return sorted(items, key=_make_key, reverse=reverse)
