#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.memoize as memoize


def test_memoize_pow() -> None:
    @memoize.MemoizeCache
    def memoized_pow(a, b):
        return a**b

    assert memoized_pow(4, 2) == 16
    assert memoized_pow(3, 2) == 9
    assert memoized_pow(4, 2) == 16
    assert memoized_pow(3, 2) == 9
    assert len(memoized_pow._cache) == 2


def test_memoize_clear() -> None:
    @memoize.MemoizeCache
    def memoized_pow(a, b):
        return a**b

    assert memoized_pow(3, 2) == 9
    assert len(memoized_pow._cache) == 1

    memoized_pow.clear()
    assert len(memoized_pow._cache) == 0

    assert memoized_pow(3, 2) == 9
    assert memoized_pow(3, 2) == 9
    assert len(memoized_pow._cache) == 1
