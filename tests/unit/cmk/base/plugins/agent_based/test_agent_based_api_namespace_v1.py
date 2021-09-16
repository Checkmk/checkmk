#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
+---------------------------------------------------------+
|              Achtung Alles Lookenskeepers!              |
|              =============================              |
|                                                         |
| The extend of the Check API is well documented, and the |
| result of careful negotiation. It should not be changed |
| light heartedly!                                        |
+---------------------------------------------------------+
"""
from cmk.base.plugins.agent_based.agent_based_api import v1


def _names(space):
    return sorted(n for n in dir(space) if not n.startswith("_"))


def test_v1():
    if _names(v1) != [
        "Attributes",
        "GetRateError",
        "HostLabel",
        "IgnoreResults",
        "IgnoreResultsError",
        "Metric",
        "OIDBytes",
        "OIDCached",
        "OIDEnd",
        "Result",
        "SNMPTree",
        "Service",
        "ServiceLabel",
        "State",
        "TableRow",
        "all_of",
        "any_of",
        "check_levels",
        "check_levels_predictive",
        "clusterize",
        "contains",
        "endswith",
        "equals",
        "exists",
        "get_average",
        "get_rate",
        "get_value_store",
        "matches",
        "not_contains",
        "not_endswith",
        "not_equals",
        "not_exists",
        "not_matches",
        "not_startswith",
        "regex",
        "register",
        "render",
        "startswith",
        "type_defs",
    ]:
        # do not output actual names. Changing this is meant to hurt!
        raise AssertionError(__doc__)


def test_v1_render():
    if _names(v1.render) != [
        "bytes",
        "date",
        "datetime",
        "disksize",
        "filesize",
        "frequency",
        "iobandwidth",
        "networkbandwidth",
        "nicspeed",
        "percent",
        "timespan",
    ]:
        raise AssertionError(__doc__)


def test_v1_type_defs():
    if _names(v1.type_defs) != [
        "CheckResult",
        "DiscoveryResult",
        "HostLabelGenerator",
        "InventoryResult",
        "StringByteTable",
        "StringTable",
    ]:
        raise AssertionError(__doc__)


def test_v1_register():
    if _names(v1.register) != [
        "RuleSetType",
        "agent_section",
        "check_plugin",
        "inventory_plugin",
        "snmp_section",
    ]:
        raise AssertionError(__doc__)


def test_v1_clusterize():
    if _names(v1.clusterize) != ["make_node_notice_results"]:
        raise AssertionError(__doc__)
