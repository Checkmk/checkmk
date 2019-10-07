# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
import pytest  # type: ignore
from testlib import import_module  # pylint: disable=import-error


@pytest.fixture(scope="module")
def check_traceroute():
    return import_module("active_checks/check_traceroute")


@pytest.mark.parametrize(
    "lines, hops_info",
    [
        ([], "0 hops"),
        # with -n
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
        ], "1 hops"),
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
            '2  33.117.16.28  14.359 ms  14.371 ms  14.434 ms',
        ], "2 hops"),
        # without -n
        ([
            'traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets',
            '1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms',
        ], "1 hops"),
        ([
            'traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets',
            '1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms',
            '2  foo-bar.x-online.net (33.117.16.28)  14.566 ms  14.580 ms  14.658 ms',
        ], "2 hops"),
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
            '2  33.117.16.28  14.359 ms  14.371 ms  14.434 ms',
            '3  * * *',
        ], "3 hops"),
        # IPv6
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms',
        ], "1 hops"),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms',
            '2  * 2001:4860:0:1::1abd (2001:4860:0:1::1abd)  225.189 ms *',
        ], "2 hops"),
        # several different answers for one hop
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], '1 hops'),
        # DNS failed
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  66.249.94.88 (66.249.94.88)  24.481 ms  24.498 ms  24.271 ms',
        ], '1 hops'),
    ])
def _test_ac_check_traceroute_no_routes(check_traceroute, lines, hops_info):
    status, info = check_traceroute.check_traceroute(lines, [])
    assert status == 0
    assert hops_info in info
    assert "missing routers: none" in info
    assert "bad routers: none" in info


@pytest.mark.parametrize(
    "lines, routes, missing_or_bad_info, expected_status",
    [
        ([], [], "missing routers: none, bad routers: none", 0),
        ([], [('w', 'foobar')], "missing routers: none, bad routers: none", 0),
        ([], [('W', 'foobar')], "missing routers: foobar(!), bad routers: none", 1),
        ([], [('W', 'foo'), ('W', 'bar')], "missing routers: foo(!), bar(!), bad routers: none", 1),
        ([], [('c', 'foobar')], "missing routers: none, bad routers: none", 0),
        ([], [('C', 'foobar')], "missing routers: foobar(!!), bad routers: none", 2),
        ([], [('C', 'foo'),
              ('C', 'bar')], "missing routers: foo(!!), bar(!!), bad routers: none", 2),
        ([], [('W', 'foo'),
              ('C', 'bar')], "missing routers: foo(!), bar(!!), bad routers: none", 2),
        # with -n
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
        ], [], "missing routers: none, bad routers: none", 0),
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
        ], [('w', '10.10.11.4')], "missing routers: none, bad routers: 10.10.11.4(!)", 1),
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
        ], [('W', 'foobar')], "missing routers: foobar(!), bad routers: none", 1),
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
        ], [('c', '10.10.11.4')], "missing routers: none, bad routers: 10.10.11.4(!!)", 2),
        ([
            'traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets',
            '1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms',
        ], [('C', 'foobar')], "missing routers: foobar(!!), bad routers: none", 2),
        # without -n
        ([
            'traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets',
            '1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms',
        ], [], "missing routers: none, bad routers: none", 0),
        ([
            'traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets',
            '1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms',
        ], [('w', '10.10.11.4')], "missing routers: none, bad routers: 10.10.11.4(!)", 1),
        ([
            'traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets',
            '1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms',
        ], [('W', 'foobar')], "missing routers: foobar(!), bad routers: none", 1),
        ([
            'traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets',
            '1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms',
        ], [('c', '10.10.11.4')], "missing routers: none, bad routers: 10.10.11.4(!!)", 2),
        ([
            'traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets',
            '1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms',
        ], [('C', 'foobar')], "missing routers: foobar(!!), bad routers: none", 2),
        # IPv6
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms',
        ], [], "missing routers: none, bad routers: none", 0),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms',
        ], [('w', '2001:2e8:665:0:2:2:0:1')
           ], "missing routers: none, bad routers: 2001:2e8:665:0:2:2:0:1(!)", 1),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms',
        ], [('W', 'foobar')], "missing routers: foobar(!), bad routers: none", 1),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms',
        ], [('c', '2001:2e8:665:0:2:2:0:1')
           ], "missing routers: none, bad routers: 2001:2e8:665:0:2:2:0:1(!!)", 2),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms',
        ], [('C', 'foobar')], "missing routers: foobar(!!), bad routers: none", 2),
        # several different answers for one hop
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [], 'missing routers: none, bad routers: none', 0),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('w', '204.152.141.11')], 'missing routers: none, bad routers: 204.152.141.11(!)', 1),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('w', '207.46.40.94')], 'missing routers: none, bad routers: 207.46.40.94(!)', 1),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('w', '204.152.141.11')], 'missing routers: none, bad routers: 204.152.141.11(!)', 1),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('w', '204.152.141.11'), ('w', '207.46.40.94'), ('w', '204.152.141.11')],
         'missing routers: none, bad routers: 204.152.141.11(!), 207.46.40.94(!), 204.152.141.11(!)',
         1),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('W', 'foobar')], 'missing routers: foobar(!), bad routers: none', 1),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('c', '204.152.141.11')], 'missing routers: none, bad routers: 204.152.141.11(!!)', 2),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('c', '207.46.40.94')], 'missing routers: none, bad routers: 207.46.40.94(!!)', 2),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('c', '204.152.141.11')], 'missing routers: none, bad routers: 204.152.141.11(!!)', 2),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('c', '204.152.141.11'), ('c', '207.46.40.94'), ('c', '204.152.141.11')],
         'missing routers: none, bad routers: 204.152.141.11(!!), 207.46.40.94(!!), 204.152.141.11(!!)',
         2),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('w', '204.152.141.11'), ('c', '207.46.40.94')
           ], 'missing routers: none, bad routers: 204.152.141.11(!), 207.46.40.94(!!)', 2),
        ([
            'traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets',
            '1 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms',
        ], [('C', 'foobar')], 'missing routers: foobar(!!), bad routers: none', 2),
    ])
def test_ac_check_traceroute_routes(check_traceroute, lines, routes, missing_or_bad_info,
                                    expected_status):
    status, info = check_traceroute.check_traceroute(lines, routes)
    assert status == expected_status
    assert info.endswith(missing_or_bad_info)
