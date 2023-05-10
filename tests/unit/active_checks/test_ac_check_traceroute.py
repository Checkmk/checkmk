#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import import_module


@pytest.fixture(name="check_traceroute", scope="module")
def fixture_check_traceroute():
    return import_module("active_checks/check_traceroute")


def test_check_traceroute_empty(check_traceroute) -> None:
    assert check_traceroute.check_traceroute([], []) == (
        0,
        "0 hops, missing routers: none, bad routers: none",
        [("hops", 0)],
    )


_TRACEROUTE_OUTPUT_IPV4 = [
    "traceroute to checkmk.com (45.133.11.28), 30 hops max, 60 byte packets",
    " 1  fritz.box (192.168.178.1)  5.401 ms  10.259 ms  10.252 ms",
    " 2  62.245.142.198 (62.245.142.198)  10.501 ms  11.724 ms  13.049 ms",
    " 3  ae0.rt-decix-3.m-online.net (212.18.6.171)  18.461 ms  21.012 ms  21.006 ms",
    " 4  fra1.mx204.ae6.de-cix.as48314.net (80.81.196.134)  23.287 ms  23.281 ms  25.486 ms",
    " 5  fra1.cc.as48314.net (194.45.196.22)  37.880 ms  37.873 ms  44.554 ms",
    " 6  * * *",
    " 7  * * *",
]


def test_check_traceroute_ipv4_no_check(check_traceroute) -> None:
    assert check_traceroute.check_traceroute(_TRACEROUTE_OUTPUT_IPV4, []) == (
        0,
        "7 hops, missing routers: none, bad routers: none",
        [("hops", 7)],
    )


def test_check_traceroute_ipv4_check_routers(check_traceroute) -> None:
    assert check_traceroute.check_traceroute(
        _TRACEROUTE_OUTPUT_IPV4,
        [("w", "63.312.142.198"), ("C", "fritz.box"), ("W", "194.45.196.22")],
    ) == (
        0,
        "7 hops, missing routers: none, bad routers: none",
        [("hops", 7)],
    )


def test_check_traceroute_ipv4_no_dns(check_traceroute) -> None:
    assert check_traceroute.check_traceroute(
        [
            "traceroute to google.com (142.250.185.110), 30 hops max, 60 byte packets",
            " 1  192.168.178.1  5.509 ms  5.473 ms  6.893 ms",
            " 2  62.245.142.198  9.617 ms  9.607 ms  18.430 ms",
            " 3  82.135.16.209  11.536 ms  15.019 ms  15.011 ms",
            " 4  142.250.161.214  13.678 ms  16.409 ms  17.603 ms",
            " 5  * * *",
            " 6  216.239.63.96  19.550 ms 108.170.228.34  14.026 ms 74.125.244.97  15.156 ms",
            " 7  108.170.247.104  14.388 ms 108.170.247.120  11.539 ms 74.125.244.82  13.174 ms",
            " 8  172.253.72.249  11.373 ms  11.394 ms  10.063 ms",
            " 9  142.250.46.170  17.180 ms 172.253.79.190  119.911 ms  118.695 ms",
            "10  209.85.252.215  16.133 ms 108.170.238.61  12.731 ms 209.85.252.215  15.088 ms",
            "11  108.170.251.193  15.111 ms 108.170.252.65  16.871 ms  16.848 ms",
            "12  142.250.226.149  13.880 ms  13.841 ms 142.250.236.31  16.692 ms",
            "13  142.250.185.110  17.907 ms  16.612 ms  16.571 ms",
        ],
        [
            ("C", "62.245.142.198"),
            ("c", "1.2.3.4"),
        ],
    ) == (
        0,
        "13 hops, missing routers: none, bad routers: none",
        [("hops", 13)],
    )


_TRACEROUTE_OUTPUT_IPV6 = [
    "traceroute to checkmk.com (2a0a:51c1:0:5::4), 30 hops max, 80 byte packets",
    " 1  fritz.box (2001:a61:433:bc01:9a9b:cbff:fe06:2f84)  6.236 ms  6.216 ms  7.319 ms",
    " 2  2001:a60::89:107:1 (2001:a60::89:107:1)  10.853 ms  10.825 ms  11.931 ms",
    " 3  2001:a60::69:0:2:3 (2001:a60::69:0:2:3)  21.008 ms  20.982 ms  20.958 ms",
    " 4  fra1.mx204.ae6.de-cix.as48314.net (2001:7f8::bcba:0:2)  23.155 ms  23.129 ms  23.103 ms",
    " 5  fra1.cc1.as48314.net (2a0a:51c1:0:4002::51)  231.003 ms !X  37.416 ms !X  230.950 ms !X",
]


def test_check_traceroute_ipv6_no_check(check_traceroute) -> None:
    assert check_traceroute.check_traceroute(_TRACEROUTE_OUTPUT_IPV6, []) == (
        0,
        "5 hops, missing routers: none, bad routers: none",
        [("hops", 5)],
    )


def test_check_traceroute_ipv6_check_routers(check_traceroute) -> None:
    assert check_traceroute.check_traceroute(
        _TRACEROUTE_OUTPUT_IPV6,
        [
            ("c", "fra1.mx204.ae6.de-cix.as48314.net"),
            ("c", "2001:a60::69:0:2:3"),
            ("W", "2001:a61:433:bc01:9a9b:cbff:fe06:2f84"),
        ],
    ) == (
        2,
        "5 hops, missing routers: none, bad routers: fra1.mx204.ae6.de-cix.as48314.net(!!), 2001:a60::69:0:2:3(!!)",
        [("hops", 5)],
    )


def test_check_traceroute_ipv6_link_local(check_traceroute) -> None:
    assert check_traceroute.check_traceroute(
        [
            "traceroute to fe80::e936:552e:d8bf:6d67%wlp0s20f3 (fe80::e936:552e:d8bf:6d67%wlp0s20f3), 30 hops max, 80 byte packets",
            " 1  klapp-0060 (fe80::e936:552e:d8bf:6d67%wlp0s20f3)  0.021 ms  0.004 ms  0.003 ms",
        ],
        [("W", "fe80::e936:552e:d8bf:6d67%wlp0s20f3")],
    ) == (
        0,
        "1 hop, missing routers: none, bad routers: none",
        [("hops", 1)],
    )


def test_check_traceroute_ipv6_no_dns(check_traceroute) -> None:
    assert check_traceroute.check_traceroute(
        [
            "traceroute to google.com (2a00:1450:4001:80e::200e), 30 hops max, 80 byte packets",
            " 1  2001:a61:433:bc01:9a9b:cbff:fe06:2f84  7.510 ms  7.477 ms  7.470 ms",
            " 2  2001:a60::89:107:1  19.835 ms  19.828 ms  19.822 ms",
            " 3  * * *",
            " 4  2001:4860:1:1::1a50  17.036 ms  17.030 ms  17.023 ms",
            " 5  2a00:1450:8018::1  19.777 ms 2a00:1450:8017::1  20.427 ms 2a00:1450:801a::1  20.421 ms",
            " 6  2001:4860:0:1::3e8a  20.415 ms 2001:4860:0:1::20ae  12.828 ms 2001:4860:0:1::4008  10.797 ms",
            " 7  2001:4860:0:110b::7  12.733 ms 2001:4860:0:12::3  9.223 ms  9.202 ms",
            " 8  2001:4860::c:4001:e5d7  15.901 ms 2001:4860::c:4001:5639  15.714 ms  14.455 ms",
            " 9  2001:4860::c:4002:365d  20.296 ms  20.285 ms  20.277 ms",
            "10  * 2001:4860::9:4001:31f2  13.854 ms *",
            "11  2001:4860:0:1::10d7  14.481 ms  14.476 ms  13.694 ms",
            "12  2001:4860:0:1::10d9  13.647 ms 2001:4860:0:1::10d7  14.743 ms 2001:4860:0:1::10d9  13.441 ms",
            "13  2a00:1450:4001:80e::200e  14.469 ms  15.243 ms  12.842 ms",
        ],
        [
            ("W", "2a00:1450:8018::1"),
            ("w", "2001:4860::9:4001:31f2"),
        ],
    ) == (
        1,
        "13 hops, missing routers: none, bad routers: 2001:4860::9:4001:31f2(!)",
        [("hops", 13)],
    )
