#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def first(iterable):
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
        return
