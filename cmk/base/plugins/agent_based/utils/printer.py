#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
# perfometer shows 'pages_total'
# checks' parse_function's output:
# { 'KEY1' : PAGES VALUE1, 'KEY2' : PAGES VALUE2, ... }
"""

from typing import Dict

from ..agent_based_api.v1 import all_of, any_of, check_levels, contains, exists, Service, startswith
from ..agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

Section = Dict[str, int]

OID_sysObjectID = ".1.3.6.1.2.1.1.2.0"

PRINTER_MANUFACTURERS = [
    ".1.3.6.1.4.1.2435.2.3.9",  # brother
    ".1.3.6.1.4.1.1602",  # canon
    ".1.3.6.1.4.1.5502",  # canon aptex
    ".1.3.6.1.4.1.25278",  # canon
    ".1.3.6.1.4.1.27748",  # canon
    ".1.3.6.1.4.1.11.2.3.9.1",  # hp
    ".1.3.6.1.4.1.18334",  # konica
    ".1.3.6.1.4.1.1347",  # kyocera
    ".1.3.6.1.4.1.2001.1",  # oki
    ".1.3.6.1.4.1.1129",  # tec
    ".1.3.6.1.4.1.367",  # ricoh
    ".1.3.6.1.4.1.236",  # samsung
    ".1.3.6.1.4.1.253.8.62.1",  # xerox
    ".1.3.6.1.4.1.683.6",  # extended systems
    ".1.3.6.1.4.1.10642",  # zebra
    ".1.3.6.1.4.1.674",  # dell
    ".1.3.6.1.4.1.345",  # epson
    ".1.3.6.1.4.1.1248",  # seiko epson
    ".1.3.6.1.4.1.641.2",  # lexmark
    ".1.3.6.1.4.1.396",  # panasonic
    ".1.3.6.1.4.1.44932",  # panasonic
    ".1.3.6.1.4.1.1472",  # sharp
    ".1.3.6.1.4.1.2385",  # sharp
    ".1.3.6.1.4.1.186",  # toshiba
    ".1.3.6.1.4.1.3835",  # ALPS
    ".1.3.6.1.4.1.2565",  # avery dennison
    ".1.3.6.1.4.1.20438",  # citizen
    ".1.3.6.1.4.1.33241",  # citizen
    ".1.3.6.1.4.1.6345",  # compuprint
    ".1.3.6.1.4.1.2125",  # comtec
    ".1.3.6.1.4.1.4228",  # dascom
    ".1.3.6.1.4.1.314",  # eastman kodak
    ".1.3.6.1.4.1.16653",  # eltron
    ".1.3.6.1.4.1.28959",  # fargo
    ".1.3.6.1.4.1.28708",  # fujifilm
    ".1.3.6.1.4.1.79",  # fujitsu
    ".1.3.6.1.4.1.211",  # fujitsu
    ".1.3.6.1.4.1.231",  # fujitsu
    ".1.3.6.1.4.1.297",  # fuji xerox
    ".1.3.6.1.4.1.3369",  # genicom
    ".1.3.6.1.4.1.116",  # hitachi
    ".1.3.6.1.4.1.2",  # ibm
    ".1.3.6.1.4.1.28918",  # infoprint
    ".1.3.6.1.4.1.3793",  # lanier
    ".1.3.6.1.4.1.11369",  # lenovo
    ".1.3.6.1.4.1.815",  # memorex telex
    ".1.3.6.1.4.1.102",  # microcom
    ".1.3.6.1.4.1.1552",  # oce
    ".1.3.6.1.4.1.279",  # olivetti
    ".1.3.6.1.4.1.10504",  # printronix
    ".1.3.6.1.4.1.24807",  # riso kagaku
    ".1.3.6.1.4.1.42406",  # sato
    ".1.3.6.1.4.1.263",  # seiko
    ".1.3.6.1.4.1.22624",  # source technologies
    ".1.3.6.1.4.1.25549",  # star
    ".1.3.6.1.4.1.128",  # tektronix
    ".1.3.6.1.4.1.294",  # texas instruments
    ".1.3.6.1.4.1.38191",  # memjet
    ".1.3.6.1.4.1.950",  # polaroid
    ".1.3.6.1.4.1.25816",  # roland dg
    ".1.3.6.1.4.1.28878",  # seikosha
    ".1.3.6.1.4.1.40463",  # troy
    ".1.3.6.1.4.1.122",  # sony
    ".1.3.6.1.4.1.119",  # NEC
]

DETECT_PRINTER_MANUFACTURER = any_of(
    *[startswith(OID_sysObjectID, oid) for oid in PRINTER_MANUFACTURERS]
)

DETECT_PRINTER = all_of(
    DETECT_PRINTER_MANUFACTURER,
    exists(".1.3.6.1.2.1.43.*"),
    exists(".1.3.6.1.2.1.43.11.1.1.6.1.1"),
)

DETECT_RICOH = all_of(
    contains(OID_sysObjectID, ".1.3.6.1.4.1.367.1.1"),
    exists(".1.3.6.1.4.1.367.3.2.1.2.19.5.1.5.1"),
)

DETECT_CANON_HAS_TOTAL = all_of(
    contains(".1.3.6.1.2.1.1.1.0", "canon"),
    exists(".1.3.6.1.4.1.1602.1.1.1.1.0"),
    exists(".1.3.6.1.4.1.1602.1.11.1.3.1.4.301"),
)

DETECT_PRINTER_PAGES = all_of(
    DETECT_PRINTER_MANUFACTURER,
    exists(".1.3.6.1.2.1.43.*"),
    exists(".1.3.6.1.2.1.43.10.2.1.4.1.1"),
)

PRINTER_PAGES_TYPES = {
    "pages_total": "total prints",
    "pages_color": "color",
    "pages_bw": "b/w",
    "pages_a4": "A4",
    "pages_a3": "A3",
    "pages_color_a4": "color A4",
    "pages_bw_a4": "b/w A4",
    "pages_color_a3": "color A3",
    "pages_bw_a3": "b/w A3",
}


def discovery_printer_pages(section: Section) -> DiscoveryResult:
    yield Service()


def check_printer_pages_types(section: Section) -> CheckResult:
    """
    >>> for result in check_printer_pages_types(
    ...     {'pages_color': 21693, 'pages_bw': 54198}):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='total prints: 75891')
    Metric('pages_total', 75891.0)
    Result(state=<State.OK: 0>, summary='b/w: 54198')
    Metric('pages_bw', 54198.0)
    Result(state=<State.OK: 0>, summary='color: 21693')
    Metric('pages_color', 21693.0)
    """
    if "pages_total" not in section:
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
