#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import overload

from cmk.gui.num_split import key_num_split


def key_natural_sort(key: str) -> tuple[int | str, ...]:
    is_symbol = not key[0].isalnum()
    is_number = key[0].isdigit()
    split = key_num_split(key.casefold())

    order = (
        (not is_number and is_symbol) * 1
        + (is_number and not is_symbol) * 2
        + (not is_number and not is_symbol) * 3
    )
    return (order, *split)


def cmp_natural_sort(a: str, b: str) -> int:
    return (key_natural_sort(a) > key_natural_sort(b)) - (key_natural_sort(a) < key_natural_sort(b))


@overload
def natural_sort(items: dict[str, str], reverse: bool = False) -> list[str]: ...


@overload
def natural_sort(items: Iterable[str], reverse: bool = False) -> list[str]: ...


def natural_sort(items: Iterable[str] | dict[str, str], reverse: bool = False) -> list[str]:
    if isinstance(items, dict):
        sorted_items = sorted(
            items.items(), key=lambda item: key_natural_sort(item[1]), reverse=reverse
        )
        return [item[0] for item in sorted_items]

    return sorted(items, key=key_natural_sort, reverse=reverse)
