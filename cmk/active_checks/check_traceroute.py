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

import argparse
import ast
import enum
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator, Sequence
from typing import assert_never


def main(argv: Sequence[str] | None = None) -> int:
    exitcode, info, perf = _check_traceroute_main(argv or sys.argv[1:])
    _output_check_result(info, perf)
    return exitcode


def _output_check_result(s: str, perfdata: Iterable[tuple[str, int]] | None) -> None:
    if perfdata:
        perfdata_output_entries = [
            "{}={}".format(p[0], ";".join(map(str, p[1:]))) for p in perfdata
        ]
        s += " | %s" % " ".join(perfdata_output_entries)
    sys.stdout.write("%s\n" % s)


def _check_traceroute_main(
    argv: Sequence[str],
) -> tuple[int, str, list[tuple[str, int]] | None]:
    os.unsetenv("LANG")

    args = _parse_arguments(argv)

    try:
        sto = _execute_traceroute(
            args.target,
            args.use_dns,
            args.probe_method,
            args.ip_address_family,
        )
        status, output, perfdata = _check_traceroute(
            sto.splitlines(),
            routers_missing_warn=args.routers_missing_warn,
            routers_missing_crit=args.routers_missing_crit,
            routers_found_warn=args.routers_found_warn,
            routers_found_crit=args.routers_found_crit,
        )
        info_text = output.strip() + "\n%s" % sto
        return status, info_text, perfdata

    except _ExecutionError as e:
        return 3, str(e), None

    except Exception as e:
        if args.debug:
            raise
        return 2, "Unhandled exception: %s" % _parse_exception(e), None


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
        type=_IPAddressFamily,
        choices=_IPAddressFamily,
        default=_IPAddressFamily.AUTO,
        metavar="IP-ADDRESS-FAMILY",
        help="Explicitly force IPv4 or IPv6 traceouting. By default, the program will choose the "
        "appropriate protocol automatically.",
    )
    parser.add_argument(
        "--probe_method",
        type=_ProbeMethod,
        choices=_ProbeMethod,
        default=_ProbeMethod.UDP,
        metavar="PROBE-METHOD",
        help="Method used for tracerouting. By default, UDP datagrams are used.",
    )
    parser.add_argument(
        "--use_dns",
        action="store_true",
        help="Use DNS to convert hostnames to IP addresses.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: let Python exceptions come through.",
    )
    return parser.parse_args(argv)


class _IPAddressFamily(enum.Enum):
    AUTO = "auto"
    v4 = "ipv4"
    v6 = "ipv6"


class _ProbeMethod(enum.Enum):
    UDP = "udp"
    ICMP = "icmp"
    TCP = "tcp"


def _execute_traceroute(
    target: str,
    use_dns: bool,
    method: _ProbeMethod,
    address_family: _IPAddressFamily,
) -> str:
    cmd = ["traceroute", target]
    if not use_dns:
        cmd.append("-n")

    match method:
        case _ProbeMethod.UDP:
            pass
        case _ProbeMethod.ICMP:
            cmd.append("-I")
        case _ProbeMethod.TCP:
            cmd.append("-T")
        case _:
            assert_never(method)

    match address_family:
        case _IPAddressFamily.AUTO:
            pass
        case _IPAddressFamily.v4:
            cmd.append("-4")
        case _IPAddressFamily.v6:
            cmd.append("-6")
        case _:
            assert_never(address_family)

    completed_process = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf8",
        check=False,
    )
    if completed_process.returncode:
        raise _ExecutionError("UNKNOWN - " + completed_process.stderr.replace("\n", " "))
    return completed_process.stdout


class _ExecutionError(Exception):
    pass


def _check_traceroute(
    lines: Sequence[str],
    *,
    routers_missing_warn: Iterable[str] = (),
    routers_missing_crit: Iterable[str] = (),
    routers_found_warn: Iterable[str] = (),
    routers_found_crit: Iterable[str] = (),
) -> tuple[int, str, list[tuple[str, int]]]:
    routers = {router for line in lines[1:] for router in _extract_routers_from_line(line)}
    n_hops = len(lines[1:])

    missing_routers_warn = [
        _mark_warning(router) for router in sorted(set(routers_missing_warn) - routers)
    ]
    missing_routers_crit = [
        _mark_critical(router) for router in sorted(set(routers_missing_crit) - routers)
    ]
    found_routers_warn = [
        _mark_warning(router) for router in sorted(set(routers_found_warn) & routers)
    ]
    found_routers_crit = [
        _mark_critical(router) for router in sorted(set(routers_found_crit) & routers)
    ]

    return (
        2
        if any(missing_routers_crit + found_routers_crit)
        else 1
        if any(missing_routers_warn + found_routers_warn)
        else 0,
        f"%d hop{'' if n_hops == 1 else 's'}, missing routers: %s, bad routers: %s"
        % (
            n_hops,
            ", ".join(missing_routers_crit + missing_routers_warn) or "none",
            ", ".join(found_routers_crit + found_routers_warn) or "none",
        ),
        [("hops", n_hops)],
    )


def _extract_routers_from_line(line: str) -> Iterator[str]:
    # drop asterisks, which mean no response from the router at this hop
    line = line.replace("*", "")
    # drop round-trip times
    line = re.sub(r"[0-9]+(\.[0-9]+)? ms", "", line)
    yield from (
        part.lstrip("(").rstrip(")")
        for part in line.strip().split()
        # drop numbering
        [1:]
        # drop additional information such as !X
        if not part.startswith("!")
    )


def _mark_warning(router: str) -> str:
    return f"{router}(!)"


def _mark_critical(router: str) -> str:
    return f"{router}(!!)"


def _parse_exception(exc: Exception) -> str:
    exc_str = str(exc)
    if exc_str[0] == "{":
        exc_str = "%d - %s" % list(ast.literal_eval(exc_str).values())[0]
    return exc_str
