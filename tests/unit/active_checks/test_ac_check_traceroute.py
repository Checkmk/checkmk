#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name
import pytest

from tests.testlib import import_module  # pylint: disable=import-error


@pytest.fixture(scope="module")
def check_traceroute():
    return import_module("active_checks/check_traceroute")


@pytest.mark.parametrize(
    "lines, hops_info, expected_perf",
    [
        ([], "0 hops", [("hops", 0)]),
        # with -n
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
            ],
            "1 hops",
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
                "2  33.117.16.28  14.359 ms  14.371 ms  14.434 ms",
            ],
            "2 hops",
            [("hops", 2)],
        ),
        # without -n
        (
            [
                "traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets",
                "1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms",
            ],
            "1 hops",
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets",
                "1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms",
                "2  foo-bar.x-online.net (33.117.16.28)  14.566 ms  14.580 ms  14.658 ms",
            ],
            "2 hops",
            [("hops", 2)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
                "2  33.117.16.28  14.359 ms  14.371 ms  14.434 ms",
                "3  * * *",
            ],
            "3 hops",
            [("hops", 3)],
        ),
        # IPv6
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms",
            ],
            "1 hops",
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms",
                "2  * 2001:4860:0:1::1abd (2001:4860:0:1::1abd)  225.189 ms *",
            ],
            "2 hops",
            [("hops", 2)],
        ),
        # several different answers for one hop
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            "1 hops",
            [("hops", 1)],
        ),
        # DNS failed
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  66.249.94.88 (66.249.94.88)  24.481 ms  24.498 ms  24.271 ms",
            ],
            "1 hops",
            [("hops", 1)],
        ),
    ],
)
def test_ac_check_traceroute_no_routes(check_traceroute, lines, hops_info, expected_perf):
    status, info, perf = check_traceroute.check_traceroute(lines, [])
    assert status == 0
    assert hops_info in info
    assert "missing routers: none" in info
    assert "bad routers: none" in info
    assert perf == expected_perf


@pytest.mark.parametrize(
    "lines, routes, missing_or_bad_info, expected_status, expected_hops",
    [
        ([], [], "missing routers: none, bad routers: none", 0, [("hops", 0)]),
        ([], [("w", "foobar")], "missing routers: none, bad routers: none", 0, [("hops", 0)]),
        ([], [("W", "foobar")], "missing routers: foobar(!), bad routers: none", 1, [("hops", 0)]),
        (
            [],
            [("W", "foo"), ("W", "bar")],
            "missing routers: foo(!), bar(!), bad routers: none",
            1,
            [("hops", 0)],
        ),
        ([], [("c", "foobar")], "missing routers: none, bad routers: none", 0, [("hops", 0)]),
        ([], [("C", "foobar")], "missing routers: foobar(!!), bad routers: none", 2, [("hops", 0)]),
        (
            [],
            [("C", "foo"), ("C", "bar")],
            "missing routers: foo(!!), bar(!!), bad routers: none",
            2,
            [("hops", 0)],
        ),
        (
            [],
            [("W", "foo"), ("C", "bar")],
            "missing routers: foo(!), bar(!!), bad routers: none",
            2,
            [("hops", 0)],
        ),
        # with -n
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
            ],
            [],
            "missing routers: none, bad routers: none",
            0,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
            ],
            [("w", "10.10.11.4")],
            "missing routers: none, bad routers: 10.10.11.4(!)",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
            ],
            [("W", "foobar")],
            "missing routers: foobar(!), bad routers: none",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
            ],
            [("c", "10.10.11.4")],
            "missing routers: none, bad routers: 10.10.11.4(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets",
                "1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms",
            ],
            [("C", "foobar")],
            "missing routers: foobar(!!), bad routers: none",
            2,
            [("hops", 1)],
        ),
        # without -n
        (
            [
                "traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets",
                "1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms",
            ],
            [],
            "missing routers: none, bad routers: none",
            0,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets",
                "1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms",
            ],
            [("w", "10.10.11.4")],
            "missing routers: none, bad routers: 10.10.11.4(!)",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets",
                "1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms",
            ],
            [("W", "foobar")],
            "missing routers: foobar(!), bad routers: none",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets",
                "1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms",
            ],
            [("c", "10.10.11.4")],
            "missing routers: none, bad routers: 10.10.11.4(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets",
                "1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms",
            ],
            [("C", "foobar")],
            "missing routers: foobar(!!), bad routers: none",
            2,
            [("hops", 1)],
        ),
        # IPv6
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms",
            ],
            [],
            "missing routers: none, bad routers: none",
            0,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms",
            ],
            [("w", "2001:2e8:665:0:2:2:0:1")],
            "missing routers: none, bad routers: 2001:2e8:665:0:2:2:0:1(!)",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms",
            ],
            [("W", "foobar")],
            "missing routers: foobar(!), bad routers: none",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms",
            ],
            [("c", "2001:2e8:665:0:2:2:0:1")],
            "missing routers: none, bad routers: 2001:2e8:665:0:2:2:0:1(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms",
            ],
            [("C", "foobar")],
            "missing routers: foobar(!!), bad routers: none",
            2,
            [("hops", 1)],
        ),
        # several different answers for one hop
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [],
            "missing routers: none, bad routers: none",
            0,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("w", "204.152.141.11")],
            "missing routers: none, bad routers: 204.152.141.11(!)",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("w", "207.46.40.94")],
            "missing routers: none, bad routers: 207.46.40.94(!)",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("w", "204.152.141.11")],
            "missing routers: none, bad routers: 204.152.141.11(!)",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("w", "204.152.141.11"), ("w", "207.46.40.94"), ("w", "204.152.141.11")],
            "missing routers: none, bad routers: 204.152.141.11(!), 207.46.40.94(!), 204.152.141.11(!)",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("W", "foobar")],
            "missing routers: foobar(!), bad routers: none",
            1,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("c", "204.152.141.11")],
            "missing routers: none, bad routers: 204.152.141.11(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("c", "207.46.40.94")],
            "missing routers: none, bad routers: 207.46.40.94(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("c", "204.152.141.11")],
            "missing routers: none, bad routers: 204.152.141.11(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("c", "204.152.141.11"), ("c", "207.46.40.94"), ("c", "204.152.141.11")],
            "missing routers: none, bad routers: 204.152.141.11(!!), 207.46.40.94(!!), 204.152.141.11(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("w", "204.152.141.11"), ("c", "207.46.40.94")],
            "missing routers: none, bad routers: 204.152.141.11(!), 207.46.40.94(!!)",
            2,
            [("hops", 1)],
        ),
        (
            [
                "traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets",
                "1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms",
            ],
            [("C", "foobar")],
            "missing routers: foobar(!!), bad routers: none",
            2,
            [("hops", 1)],
        ),
    ],
)
def test_ac_check_traceroute_routes(
    check_traceroute, lines, routes, missing_or_bad_info, expected_status, expected_hops
):
    status, info, perf = check_traceroute.check_traceroute(lines, routes)
    assert status == expected_status
    assert info.endswith(missing_or_bad_info)
    assert perf == expected_hops
