#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
'''
# perfometer shows 'pages_total'
# checks' parse_function's output:
# { 'KEY1' : PAGES VALUE1, 'KEY2' : PAGES VALUE2, ... }
'''

from typing import Dict

from ..agent_based_api.v1 import (
    Service,
    all_of,
    contains,
    exists,
    check_levels,
)
from ..agent_based_api.v1.type_defs import DiscoveryResult, CheckResult

Section = Dict[str, int]

OID_sysObjectID = ".1.3.6.1.2.1.1.2.0"

DETECT_RICOH = all_of(
    contains(OID_sysObjectID, ".1.3.6.1.4.1.367.1.1"),
    exists(".1.3.6.1.4.1.367.3.2.1.2.19.5.1.5.1"),
)

DETECT_CANON_HAS_TOTAL = all_of(
    contains(".1.3.6.1.2.1.1.1.0", "canon"),
    exists(".1.3.6.1.4.1.1602.1.1.1.1.0"),
    exists(".1.3.6.1.4.1.1602.1.11.1.3.1.4.301"),
)

DETECT_GENERIC = exists(".1.3.6.1.2.1.43.10.2.1.4.1.1")

PRINTER_PAGES_TYPES = {
    'pages_total': 'total prints',
    'pages_color': 'color',
    'pages_bw': 'b/w',
    'pages_a4': 'A4',
    'pages_a3': 'A3',
    'pages_color_a4': 'color A4',
    'pages_bw_a4': 'b/w A4',
    'pages_color_a3': 'color A3',
    'pages_bw_a3': 'b/w A3',
}


def discovery_printer_pages(section: Section) -> DiscoveryResult:
    yield Service()


def check_printer_pages_types(section: Section) -> CheckResult:
    """
    >>> for result in check_printer_pages_types(
    ...     {'pages_color': 21693, 'pages_bw': 54198}):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='total prints: 75891', details='total prints: 75891')
    Metric('pages_total', 75891.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='b/w: 54198', details='b/w: 54198')
    Metric('pages_bw', 54198.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='color: 21693', details='color: 21693')
    Metric('pages_color', 21693.0, levels=(None, None), boundaries=(None, None))
    """
    if 'pages_total' not in section:
        yield from check_levels(
            value=sum(section.values()),
            render_func=str,
            metric_name="pages_total",
            label="total prints",
        )

    for pages_type, pages in sorted(section.items()):
        if pages_type in PRINTER_PAGES_TYPES:
            yield from check_levels(
                value=pages,
                render_func=str,
                metric_name=pages_type,
                label=PRINTER_PAGES_TYPES[pages_type],
            )
