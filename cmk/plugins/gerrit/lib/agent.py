#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_gerrit

Checkmk special agent to monitor gerrit instances.
"""

import argparse
import dataclasses
import json
import sys
from collections.abc import Sequence
from typing import NewType

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.plugins.gerrit.lib.cache import cache_ttl
from cmk.plugins.gerrit.lib.collectors import Collector, GerritVersion
from cmk.plugins.gerrit.lib.schema import VersionInfo
from cmk.server_side_programs.v1_unstable import report_agent_crashes, Storage, vcrtrace

__version__ = "2.5.0p14"

AGENT = "gerrit"

PASSWORD_OPTION = "password"


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    args = parse_arguments(sys.argv[1:])

    api_url = f"{args.proto}://{args.hostname}:{args.port}/a"
    auth = (args.user, resolve_secret_option(args, PASSWORD_OPTION).reveal())

    ctx = GerritRunContext(
        hostname=args.hostname,
        ttl=TTLCache(version=int(args.version_cache)),
        collectors=Collectors(version=GerritVersion(api_url=api_url, auth=auth)),
    )

    return run(ctx)


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n")
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )

    parser.add_argument("-u", "--user", default="", help="Username for Gerrit login")
    parser_add_secret_option(
        parser, long=f"--{PASSWORD_OPTION}", required=True, help="Password for Gerrit login"
    )
    parser.add_argument(
        "--version-cache",
        default=28800.0,  # 8 hours
        type=float,
        help="Cache interval in seconds for Gerrit version collection (default: 28800.0 [8h])",
    )
    parser.add_argument(
        "-P",
        "--proto",
        choices=("https", "http"),
        default="https",
        help="Protocol (default: 'https')",
    )
    parser.add_argument("-p", "--port", default=443, type=int, help="Port (default: 443)")
    parser.add_argument("hostname", metavar="HOSTNAME", help="Hostname of Gerrit instance.")

    return parser.parse_args(argv)


@dataclasses.dataclass(frozen=True, kw_only=True)
class TTLCache:
    version: int


@dataclasses.dataclass(frozen=True, kw_only=True)
class Collectors:
    version: Collector[VersionInfo]


@dataclasses.dataclass(frozen=True, kw_only=True)
class GerritRunContext:
    hostname: str
    ttl: TTLCache
    collectors: Collectors


def run(ctx: GerritRunContext) -> int:
    process_version_section(ctx)

    return 0


def process_version_section(ctx: GerritRunContext) -> None:
    name = "gerrit_version"
    storage = Storage(name, ctx.hostname)
    cache_wrapper = cache_ttl(storage, ttl=ctx.ttl.version)
    data, ts = cache_wrapper(ctx.collectors.version.collect)()
    cache_marker = build_cache_marker(ts=ts, ttl=ctx.ttl.version) if ts is not None else None
    write_section(data, name=name, cache_marker=cache_marker)


Marker = NewType("Marker", str)
"""Marker indicates that a string is prefixed with a colon and can be added to a section header."""


def build_cache_marker(ts: float, ttl: int) -> Marker:
    return Marker(f":cached({int(ts)},{ttl})")


def write_section(data: object, *, name: str, cache_marker: Marker | None = None) -> None:
    header = f"{name}:sep(0){cache_marker or ''}"
    content = json.dumps(data, sort_keys=True)

    sys.stdout.write(f"<<<{header}>>>\n")
    sys.stdout.write(f"{content}\n")


if __name__ == "__main__":
    sys.exit(main())
