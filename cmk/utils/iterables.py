#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Iterable, List, Optional, Tuple, TypeVar

T = TypeVar("T")


def first(iterable: Iterable[T]) -> Optional[T]:
    """Return the first element of an iterable or None if it is empty.

    Examples:

        >>> first([1, 2, 3])
        1

        >>> first([])

    Args:
        iterable (Iterable): Something that supports Python's iterator protocol.

    Returns:
        The first entry of the iterable or None
    """
    try:
        return next(iter(iterable))
    except StopIteration:
        return None


def partition(pred: Callable[[T], bool], iterable: Iterable[T]) -> Tuple[List[T], List[T]]:
    yay: List[T] = []
    nay: List[T] = []
    for x in iterable:
        (yay if pred(x) else nay).append(x)
    return yay, nay
