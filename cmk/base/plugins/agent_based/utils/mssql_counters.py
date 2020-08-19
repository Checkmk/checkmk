#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
# There are different types of information. Can we handle them in a
# general way? There are:
#  - Percentage values
#  - Size values in KB
#  - Counters
#  - Rate counters (per second)

inventory_mssql_counters_rules = []

#TODO if not counters: raise


def inventory_mssql_counters_generic(parsed, want_counters, dflt=None):
    want_counters = set(want_counters)
    for (obj, instance), node_data in parsed.items():
        for counters in node_data.values():
            if not want_counters.intersection(counters):
                continue
            yield "%s %s" % (obj, instance), dflt


# Previously there was no main check, but we need it because
# the sub checks
# - mssql_counters.transactions
# - mssql_counters.pageactivity
# - mssql_counters.locks
# will become cluster aware and thus all subchecks, too, because they share
# the same section. This main check is just a dummy with the benefit of the
# parse function.


def extract_item_data(item, parsed):
    obj, instance, *_ = item.split()
    return {
        node_name: node_data[(obj, instance)]
        for node_name, node_data in parsed.items()
        if (obj, instance) in node_data
    } or None
"""
