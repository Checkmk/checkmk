#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math


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

    index = int(_py2_compatible_round(target_index))
    if int(target_index) == index and index < len(ordered) - 1:
        return (ordered[index] + ordered[index + 1]) / 2.0
    return ordered[index]


# TODO: Please check whether or not this is really what we want here.
def _py2_compatible_round(x, d=0):
    # type: (float, int) -> float
    p = 10**d
    if x > 0:
        return float(math.floor((x * p) + 0.5)) / p
    return float(math.ceil((x * p) - 0.5)) / p
