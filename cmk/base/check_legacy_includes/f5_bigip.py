#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def get_conn_rate_params(params):
    # upper_bound is dict, tuple or None
    upper_bound = params.get("connections_rate", (None, None))
    # lower_bound is tuple or None
    lower_bound = params.get("connections_rate_lower", (None, None))
    if isinstance(upper_bound, tuple):
        return upper_bound + lower_bound

    # Lower bound was not configured, all good
    if isinstance(upper_bound, dict) and lower_bound == (None, None):
        return upper_bound
    raise ValueError(
        "Can't configure minimum connections per second when the maximum "
        "connections per second is setup in predictive levels. Please use the given "
        "lower bound specified in the maximum connections, or set maximum "
        "connections to use fixed levels."
    )
