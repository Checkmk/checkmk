#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Callable, TypeVar

T = TypeVar("T")


def partition(pred: Callable[[T], bool], iterable: Iterable[T]) -> tuple[list[T], list[T]]:
    yay: list[T] = []
    nay: list[T] = []
    for x in iterable:
        (yay if pred(x) else nay).append(x)
    return yay, nay
