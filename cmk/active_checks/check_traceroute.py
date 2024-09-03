#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This check does a traceroute to the specified target host
# (usually $HOSTADDRESS$ itself) and checks which route(s) are
# being taken. That way you can check if your preferred or
# some alternative route in in place.
# traceroute is expected to be in the search path and installed
# with SUID root bit.

# Example output from traceroute -n
# traceroute to www.google.de (173.194.44.55), 30 hops max, 60 byte packets
#  1  10.10.11.4  0.419 ms  0.444 ms  0.518 ms
#  2  33.117.16.28  14.359 ms  14.371 ms  14.434 ms
#  3  112.18.7.119  14.750 ms  14.765 ms  19.530 ms
#  4  184.50.190.61  17.844 ms  17.865 ms  17.862 ms
#  5  67.249.94.88  24.285 ms  78.527 ms  26.834 ms
#  6  209.85.240.99  27.910 ms  27.420 ms  27.442 ms
#  7  173.194.44.55  26.583 ms  20.410 ms  23.142 ms

# Output without -n option:
# traceroute to www.google.de (173.194.44.56), 30 hops max, 60 byte packets
#  1  fritz.box (10.10.11.4)  0.570 ms  0.606 ms  0.677 ms
#  2  foo-bar.x-online.net (33.117.16.28)  14.566 ms  14.580 ms  14.658 ms
#  3  xu-2-3-0.rt-inxs-1.x-online.net (112.13.6.109)  18.214 ms  18.228 ms  18.221 ms
#  4  * * *
#  5  66.249.94.88 (66.249.94.88)  24.481 ms  24.498 ms  24.271 ms
#  6  209.85.240.99 (209.85.240.99)  27.628 ms  21.605 ms  21.943 ms
#  7  muc03s08-in-f24.1e100.net (173.194.44.56)  21.277 ms  22.236 ms  22.192 ms

# Example output for IPv6
# traceroute to ipv6.google.com (2404:6800:4004:80e::200e), 30 hops max, 80 byte packets
#  1  2001:2e8:665:0:2:2:0:1 (2001:2e8:665:0:2:2:0:1)  0.082 ms  0.046 ms  0.044 ms
#  2  2001:2e8:22:204::2 (2001:2e8:22:204::2)  0.893 ms  0.881 ms  0.961 ms
#  3  * 2001:4860:0:1::1abd (2001:4860:0:1::1abd)  225.189 ms *
#  4  2001:4860:0:1003::1 (2001:4860:0:1003::1)  3.052 ms  2.820 ms 2001:4860:0:1002::1 (2001:4860:0:1002::1)  1.501 ms
#  5  nrt13s48-in-x0e.1e100.net (2404:6800:4004:80e::200e)  1.910 ms  1.828 ms  1.753 ms

# It is also possible that for one hop several different answers appear:
# 11 xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.185 ms xe-10-0-2-0.co1-96c-1a.ntwk.msn.net (207.46.40.94)  174.279 ms xe-0-0-1-0.co2-96c-1b.ntwk.msn.net (204.152.141.11)  174.444 ms

# if DNS fails then it looks like this:
#  5  66.249.94.88 (66.249.94.88)  24.481 ms  24.498 ms  24.271 ms
#  6  209.85.240.99 (209.85.240.99)  27.628 ms  21.605 ms  21.943 ms

from __future__ import annotations

import argparse
import enum
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import assert_never, Protocol


def main(
    argv: Sequence[str] | None = None,
    routetracer: RoutetracerProto | None = None,
) -> int:
    exitcode, info, perf = _check_traceroute_main(
        argv or sys.argv[1:],
        routetracer or _TracerouteRoutertrace(),
    )
    _output_check_result(info, perf)
    return exitcode


class RoutetracerProto(Protocol):
    def __call__(
        self,
        target: str,
        *,
        use_dns: bool,
        probe_method: ProbeMethod,
        ip_address_family: IPAddressFamily,
    ) -> Route: ...


class ProbeMethod(enum.Enum):
    UDP = "udp"
    ICMP = "icmp"
    TCP = "tcp"


class IPAddressFamily(enum.Enum):
    AUTO = "auto"
    v4 = "ipv4"
    v6 = "ipv6"


@dataclass(frozen=True)
class Route:
    routers: set[str]
    n_hops: int
    human_readable_route: str


def _output_check_result(s: str, perfdata: Iterable[tuple[str, int]] | None) -> None:
    if perfdata:
        perfdata_output_entries = [
            "{}={}".format(p[0], ";".join(map(str, p[1:]))) for p in perfdata
        ]
        s += " | %s" % " ".join(perfdata_output_entries)
    sys.stdout.write("%s\n" % s)


def _check_traceroute_main(
    argv: Sequence[str],
    routetracer: RoutetracerProto,
) -> tuple[int, str, list[tuple[str, int]] | None]:
    args = _parse_arguments(argv)

    try:
        return _check_route(
            routetracer(
                args.target,
                use_dns=args.use_dns,
                probe_method=args.probe_method,
                ip_address_family=args.ip_address_family,
            ),
            routers_missing_warn=args.routers_missing_warn,
            routers_missing_crit=args.routers_missing_crit,
            routers_found_warn=args.routers_found_warn,
            routers_found_crit=args.routers_found_crit,
        )

    except _RoutetracingError as e:
        return 3, str(e), None

    except Exception as e:
        if args.debug:
            raise
        return 2, f"Unhandled exception: {e}", None


def _parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check the route to a network host using the traceroute command.",
    )
    parser.add_argument(
        "target",
        type=str,
        metavar="TARGET",
        help="Can be specified either as an IP address or as a domain name.",
    )
    parser.add_argument(
        "--routers_missing_warn",
        type=str,
        nargs="*",
        metavar="ROUTER1 ROUTER2 ...",
        help="Report WARNING if any of these routers is not used.",
        default=[],
    )
    parser.add_argument(
        "--routers_missing_crit",
        type=str,
        nargs="*",
        metavar="ROUTER1 ROUTER2 ...",
        help="Report CRITICAL if any of these routers is not used.",
        default=[],
    )
    parser.add_argument(
        "--routers_found_warn",
        type=str,
        nargs="*",
        metavar="ROUTER1 ROUTER2 ...",
        help="Report WARNING if any of these routers is used.",
        default=[],
    )
    parser.add_argument(
        "--routers_found_crit",
        type=str,
        nargs="*",
        metavar="ROUTER1 ROUTER2 ...",
        help="Report CRITICAL if any of these routers is used.",
        default=[],
    )
    parser.add_argument(
        "--ip_address_family",
        type=IPAddressFamily,
        choices=IPAddressFamily,
        default=IPAddressFamily.AUTO,
        metavar="IP-ADDRESS-FAMILY",
        help="Explicitly force IPv4 or IPv6 traceouting. By default, the program will choose the "
        "appropriate protocol automatically.",
    )
    parser.add_argument(
        "--probe_method",
        type=ProbeMethod,
        choices=ProbeMethod,
        default=ProbeMethod.UDP,
        metavar="PROBE-METHOD",
        help="Method used for tracerouting. By default, UDP datagrams are used.",
    )
    parser.add_argument(
        "--use_dns",
        action="store_true",
        help="Use DNS to convert host names to IP addresses.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: let Python exceptions come through.",
    )
    return parser.parse_args(argv)


class _RoutetracingError(Exception):
    pass


def _check_route(
    route: Route,
    *,
    routers_missing_warn: Iterable[str] = (),
    routers_missing_crit: Iterable[str] = (),
    routers_found_warn: Iterable[str] = (),
    routers_found_crit: Iterable[str] = (),
) -> tuple[int, str, list[tuple[str, int]]]:
    missing_routers_warn = [
        _mark_warning(router) for router in sorted(set(routers_missing_warn) - route.routers)
    ]
    missing_routers_crit = [
        _mark_critical(router) for router in sorted(set(routers_missing_crit) - route.routers)
    ]
    found_routers_warn = [
        _mark_warning(router) for router in sorted(set(routers_found_warn) & route.routers)
    ]
    found_routers_crit = [
        _mark_critical(router) for router in sorted(set(routers_found_crit) & route.routers)
    ]

    return (
        (
            2
            if any(missing_routers_crit + found_routers_crit)
            else 1
            if any(missing_routers_warn + found_routers_warn)
            else 0
        ),
        f"%d hop{'' if route.n_hops == 1 else 's'}, missing routers: %s, bad routers: %s\n%s"
        % (
            route.n_hops,
            ", ".join(missing_routers_crit + missing_routers_warn) or "none",
            ", ".join(found_routers_crit + found_routers_warn) or "none",
            route.human_readable_route,
        ),
        [("hops", route.n_hops)],
    )


def _mark_warning(router: str) -> str:
    return f"{router}(!)"


def _mark_critical(router: str) -> str:
    return f"{router}(!!)"


class _TracerouteRoutertrace:
    def __call__(
        self,
        target: str,
        *,
        use_dns: bool,
        probe_method: ProbeMethod,
        ip_address_family: IPAddressFamily,
    ) -> Route:
        traceroute_stdout = self._execute_traceroute(
            target,
            use_dns=use_dns,
            probe_method=probe_method,
            ip_address_family=ip_address_family,
        )
        router_lines = traceroute_stdout.splitlines()[1:]
        return Route(
            {router for line in router_lines for router in self._extract_routers_from_line(line)},
            len(router_lines),
            traceroute_stdout,
        )

    @staticmethod
    def _execute_traceroute(
        target: str,
        *,
        use_dns: bool,
        probe_method: ProbeMethod,
        ip_address_family: IPAddressFamily,
    ) -> str:
        cmd = ["traceroute", target]
        if not use_dns:
            cmd.append("-n")

        match probe_method:
            case ProbeMethod.UDP:
                pass
            case ProbeMethod.ICMP:
                cmd.append("-I")
            case ProbeMethod.TCP:
                cmd.append("-T")
            case _:
                assert_never(probe_method)

        match ip_address_family:
            case IPAddressFamily.AUTO:
                pass
            case IPAddressFamily.v4:
                cmd.append("-4")
            case IPAddressFamily.v6:
                cmd.append("-6")
            case _:
                assert_never(ip_address_family)

        completed_process = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf8",
            check=False,
            env={k: v for k, v in os.environ.items() if k != "LANG"},
        )
        if completed_process.returncode:
            raise _RoutetracingError(f"traceroute command failed: {completed_process.stderr}")
        return completed_process.stdout

    @staticmethod
    def _extract_routers_from_line(line: str) -> Iterator[str]:
        """
        >>> list(_TracerouteRoutertrace._extract_routers_from_line('10  209.85.252.215  16.133 ms 108.170.238.61  12.731 ms 209.85.252.215  15.088 ms'))
        ['209.85.252.215', '108.170.238.61', '209.85.252.215']
        >>> list(_TracerouteRoutertrace._extract_routers_from_line(' 5  fra1.cc1.as48314.net (2a0a:51c1:0:4002::51)  231.003 ms !X  37.416 ms !X  230.950 ms !X 2001:4860:0:1::10d9  13.441 ms *'))
        ['fra1.cc1.as48314.net', '2a0a:51c1:0:4002::51', '2001:4860:0:1::10d9']
        >>> list(_TracerouteRoutertrace._extract_routers_from_line(' 7  * * *'))
        []
        """
        # drop asterisks, which mean no response from the router at this hop
        line = line.replace("*", "")
        # drop round-trip times
        line = re.sub(r"[0-9]+(\.[0-9]+)? ms", "", line)
        yield from (
            part.lstrip("(").rstrip(")")
            for part in line.strip().split()[
                # drop numbering
                1:
            ]
            # drop additional information such as !X
            if not part.startswith("!")
        )
