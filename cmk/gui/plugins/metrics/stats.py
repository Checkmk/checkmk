#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def percentile(array, q):
    """
    Return the q-th percentile of the data in array. Using midpoint interpolation.

    Parameters
    ----------
    array : array_like
        Input array or list, assumes non-empty
    q : float
        Percentile to compute, which must be between 0 and 100 inclusive"""

    ordered = sorted(array)
    target_index = q / 100.0 * len(ordered) - 1
    if target_index < 0:
        return ordered[0]

    index = int(round(target_index))
    if int(target_index) == index and index < len(ordered) - 1:
        return (ordered[index] + ordered[index + 1]) / 2.0
    return ordered[index]
