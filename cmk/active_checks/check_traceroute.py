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

import ast
import getopt
import ipaddress
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator, Sequence


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


def _check_traceroute_main(  # pylint: disable=too-many-branches
    argv: Sequence[str],
) -> tuple[int, str, list[tuple[str, int]] | None]:
    os.unsetenv("LANG")

    opt_verbose = 0
    opt_debug = False
    opt_nodns = False
    opt_method = None
    opt_address_family = None

    short_options = "hw:W:c:C:nTI46"
    long_options = [
        "verbose",
        "help",
        "debug",
    ]

    route_params = []

    try:
        opts, args = getopt.getopt(list(argv), short_options, long_options)

        for o, a in opts:
            if o in ["-h", "--help"]:
                _usage()
                sys.exit(0)

        if len(args) < 1:
            raise _MissingValueError("Please specify the target destination.")

        target_address = args[0]

        # first parse modifers
        for o, a in opts:
            if o in ["-v", "--verbose"]:
                opt_verbose += 1
            elif o in ["-d", "--debug"]:
                opt_debug = True
            elif o in ["-w", "-W", "-c", "-C"]:
                route_params.append((o[1], a))
            elif o == "-n":
                opt_nodns = True
            elif o in ["-T", "-I"]:
                opt_method = o
            elif o in ["-4", "-6"]:
                if opt_address_family:
                    raise _ProtocolVersionError("Cannot use both IPv4 and IPv6")
                _validate_ip_version(target_address, int(o.lstrip("-")))
                opt_address_family = o

        sto = _execute_traceroute(target_address, opt_nodns, opt_method, opt_address_family)
        status, output, perfdata = _check_traceroute(sto.splitlines(), route_params)
        info_text = output.strip() + "\n%s" % sto
        return status, info_text, perfdata

    except _ExecutionError as e:
        return 3, str(e), None

    except _MissingValueError as e:
        return 3, str(e), None

    except _ProtocolVersionError as e:
        return 3, str(e), None

    except Exception as e:
        if opt_debug:
            raise
        return 2, "Unhandled exception: %s" % _parse_exception(e), None


def _usage() -> None:
    sys.stdout.write(
        """check_traceroute -{c|w|C|W} ROUTE  [-{o|c|w|O|C|W} ROUTE...] TARGET

Check by which routes TARGET is being reached. Each possible route is being
prefixed with a state option:

 -w Make outcome WARN if that route is present
 -W Make outcome WARN if that route is missing
 -c Make outcome CRIT if that route is present
 -C Make outcome CRIT if that route is missing

Other options:

 -h, --help     show this help and exit
 --debug        show Python exceptions verbosely
 -n             disable reverse DNS lookups
 -I             Use ICMP ECHO for probes
 -T             Use TCP SYN for probes
 -4             Use IPv4
 -6             Use IPv6

"""
    )


class _MissingValueError(Exception):
    pass


class _ProtocolVersionError(Exception):
    pass


def _validate_ip_version(address_arg: str, ip_version_arg: int) -> None:
    # ipv6 address can have an appended interface index/name: 'fe80::%{interface}'
    try:
        ip_address_version = ipaddress.ip_interface(address_arg.split("%")[0]).ip.version
    except ValueError:
        # May be a host or DNS name, don't execute the validation in this case.
        # check_traceroute will perform the name resolution for us.
        return

    if not ip_address_version == ip_version_arg:
        raise _ProtocolVersionError(
            'IP protocol version "%s" not the same as the IP address version "%s".'
            % (ip_version_arg, ip_address_version)
        )


def _execute_traceroute(
    target: str,
    nodns: bool,
    method: str | None,
    address_family: str | None,
) -> str:
    cmd = ["traceroute"]
    if nodns:
        cmd.append("-n")
    if method:
        cmd.append(method)
    if address_family:
        cmd.append(address_family)
    cmd.append(target)
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
    routes: Iterable[tuple[str, str]],
) -> tuple[int, str, list[tuple[str, int]]]:
    # find all visited routers
    routers = {router for line in lines[1:] for router in _extract_routers_from_line(line)}
    hops = len(lines[1:])

    state = 0
    bad_routers = []
    missing_routers = []
    for option, route in routes:
        s = _option_to_state(option)
        if option.islower() and route in routers:
            state = max(state, s)
            bad_routers.append("{}({})".format(route, "!" * s))
        elif option.isupper() and route not in routers:
            state = max(state, s)
            missing_routers.append("{}({})".format(route, "!" * s))

    info_text = f"%d hop{'' if hops == 1 else 's'}, missing routers: %s, bad routers: %s" % (
        hops,
        missing_routers and ", ".join(missing_routers) or "none",
        bad_routers and ", ".join(bad_routers) or "none",
    )
    perfdata = [("hops", hops)]
    return state, info_text, perfdata


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


def _option_to_state(c: str) -> int:
    return {"w": 1, "c": 2}[c.lower()]


def _parse_exception(exc: Exception) -> str:
    exc_str = str(exc)
    if exc_str[0] == "{":
        exc_str = "%d - %s" % list(ast.literal_eval(exc_str).values())[0]
    return exc_str
