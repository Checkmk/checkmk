#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.mtr import Hop, parse_mtr

SECTION = {
    "ipv6.google.com": [],
    "mathias-kettner.de": [
        Hop(
            name="1.2.3.4",
            pl=0.0,
            response_time=0.0013,
            rta=0.0022,
            rtmin=0.0012,
            rtmax=0.007,
            rtstddev=0.0016,
        ),
        Hop(
            name="232.142.105.70",
            pl=0.0,
            response_time=0.0018,
            rta=0.0027,
            rtmin=0.0015,
            rtmax=0.0044,
            rtstddev=0.0011,
        ),
        Hop(
            name="146.26.170.63",
            pl=0.0,
            response_time=0.017,
            rta=0.016800000000000002,
            rtmin=0.0145,
            rtmax=0.019899999999999998,
            rtstddev=0.0012,
        ),
        Hop(
            name="195.164.42.167",
            pl=0.0,
            response_time=0.0172,
            rta=0.0184,
            rtmin=0.0155,
            rtmax=0.0254,
            rtstddev=0.0027,
        ),
        Hop(
            name="145.111.28.11",
            pl=0.0,
            response_time=0.0212,
            rta=0.019600000000000003,
            rtmin=0.0162,
            rtmax=0.0298,
            rtstddev=0.0040999999999999995,
        ),
        Hop(
            name="98.216.107.58",
            pl=0.0,
            response_time=0.0554,
            rta=0.0533,
            rtmin=0.0281,
            rtmax=0.1281,
            rtstddev=0.0281,
        ),
    ],
    "www.google.com": [
        Hop(
            name="1.2.3.4",
            pl=0.0,
            response_time=0.0014,
            rta=0.0016,
            rtmin=0.0014,
            rtmax=0.0022,
            rtstddev=0.0,
        ),
        Hop(
            name="232.142.105.70",
            pl=0.0,
            response_time=0.0165,
            rta=0.0179,
            rtmin=0.0035,
            rtmax=0.027,
            rtstddev=0.0065,
        ),
        Hop(
            name="ae0.rt-inxs-1.m-online.net",
            pl=0.0,
            response_time=0.0156,
            rta=0.0184,
            rtmin=0.0149,
            rtmax=0.0252,
            rtstddev=0.0033,
        ),
        Hop(
            name="whatever",
            pl=0.0,
            response_time=0.015300000000000001,
            rta=0.019100000000000002,
            rtmin=0.0145,
            rtmax=0.032299999999999995,
            rtstddev=0.0052,
        ),
        Hop(
            name="210.233.222.159",
            pl=0.0,
            response_time=0.0156,
            rta=0.018699999999999998,
            rtmin=0.0156,
            rtmax=0.0211,
            rtstddev=0.0018,
        ),
        Hop(
            name="9.32.75.54",
            pl=0.0,
            response_time=0.019,
            rta=0.020300000000000002,
            rtmin=0.0149,
            rtmax=0.0303,
            rtstddev=0.0048,
        ),
        Hop(
            name="7.69.211.19",
            pl=0.0,
            response_time=0.0247,
            rta=0.027800000000000002,
            rtmin=0.023399999999999997,
            rtmax=0.0432,
            rtstddev=0.0058,
        ),
        Hop(
            name="145.80.196.60",
            pl=0.0,
            response_time=0.0255,
            rta=0.0247,
            rtmin=0.0222,
            rtmax=0.0263,
            rtstddev=0.0009,
        ),
        Hop(
            name="0.253.40.93",
            pl=0.0,
            response_time=0.023899999999999998,
            rta=0.0229,
            rtmin=0.0212,
            rtmax=0.023899999999999998,
            rtstddev=0.0007,
        ),
        Hop(
            name="85.26.182.623",
            pl=0.0,
            response_time=0.0237,
            rta=0.024,
            rtmin=0.0202,
            rtmax=0.027100000000000003,
            rtstddev=0.0022,
        ),
        Hop(
            name="last-host.net",
            pl=0.0,
            response_time=0.023399999999999997,
            rta=0.023600000000000003,
            rtmin=0.0215,
            rtmax=0.026600000000000002,
            rtstddev=0.0015,
        ),
    ],
}


def test_parse_mtr() -> None:
    assert parse_mtr([
        [
            "www.google.com", "1550068434", "11", "1.2.3.4", "0.0%", "10", "1.4", "1.6", "1.4",
            "2.2", "0.0", "232.142.105.70", "0.0%", "10", "16.5", "17.9", "3.5", "27.0", "6.5",
            "ae0.rt-inxs-1.m-online.net", "0.0%", "10", "15.6", "18.4", "14.9", "25.2", "3.3",
            "whatever", "0.0%", "10", "15.3", "19.1", "14.5", "32.3", "5.2", "210.233.222.159",
            "0.0%", "10", "15.6", "18.7", "15.6", "21.1", "1.8", "9.32.75.54", "0.0%", "10", "19.0",
            "20.3", "14.9", "30.3", "4.8", "7.69.211.19", "0.0%", "10", "24.7", "27.8", "23.4",
            "43.2", "5.8", "145.80.196.60", "0.0%", "10", "25.5", "24.7", "22.2", "26.3", "0.9",
            "0.253.40.93", "0.0%", "10", "23.9", "22.9", "21.2", "23.9", "0.7", "85.26.182.623",
            "0.0%", "10", "23.7", "24.0", "20.2", "27.1", "2.2", "last-host.net", "0.0%", "10",
            "23.4", "23.6", "21.5", "26.6", "1.5"
        ],
        ["ipv6.google.com", "1550068434", "0"],
        [
            "mathias-kettner.de", "1550068434", "6", "1.2.3.4", "0.0%", "10", "1.3", "2.2", "1.2",
            "7.0", "1.6", "232.142.105.70", "0.0%", "10", "1.8", "2.7", "1.5", "4.4", "1.1",
            "146.26.170.63", "0.0%", "10", "17.0", "16.8", "14.5", "19.9", "1.2", "195.164.42.167",
            "0.0%", "10", "17.2", "18.4", "15.5", "25.4", "2.7", "145.111.28.11", "0.0%", "10",
            "21.2", "19.6", "16.2", "29.8", "4.1", "98.216.107.58", "0.0%", "10", "55.4", "53.3",
            "28.1", "128.1", "28.1"
        ],
    ]) == SECTION
