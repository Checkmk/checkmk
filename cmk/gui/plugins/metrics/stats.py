#!/usr/bin/env python3
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
    target_index = q / 100.0 * len(ordered) - 0.5
    if target_index < 0:
        return ordered[0]

    index_f = int(math.floor(target_index))
    index_c = int(math.ceil(target_index))

    if index_f == index_c or index_c > len(ordered) - 1:
        return ordered[index_f]

    return (ordered[index_f] + ordered[index_c]) / 2.0
