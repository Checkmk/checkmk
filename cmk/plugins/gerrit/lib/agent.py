#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import dataclasses
import json
import sys
from collections.abc import Sequence

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.plugins.gerrit.lib.cache import cache_ttl
from cmk.plugins.gerrit.lib.collectors import Collector, GerritVersion
from cmk.plugins.gerrit.lib.schema import VersionInfo
from cmk.server_side_programs.v1_unstable import report_agent_crashes, Storage, vcrtrace

__version__ = "2.5.0b1"

AGENT = "gerrit"

PASSWORD_OPTION = "password"


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    args = parse_arguments(sys.argv[1:])

    api_url = f"{args.proto}://{args.hostname}:{args.port}/a"
    auth = (args.user, resolve_secret_option(args, PASSWORD_OPTION).reveal())

    ctx = GerritRunContext(
        hostname=args.hostname,
        ttl=TTLCache(version=args.version_cache),
        collectors=Collectors(version=GerritVersion(api_url=api_url, auth=auth)),
    )

    return run(ctx)


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
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
    version_storage = Storage(f"{AGENT}_version", ctx.hostname)
    version_cache = cache_ttl(version_storage, ttl=ctx.ttl.version)
    collect_version = version_cache(ctx.collectors.version.collect)
    _write_section(collect_version(), name="gerrit_version")

    return 0


def _write_section(data: object, *, name: str) -> None:
    section_payload = json.dumps(data, sort_keys=True)
    sys.stdout.write(f"<<<{name}:sep(0)>>>\n")
    sys.stdout.write(f"{section_payload}\n")


if __name__ == "__main__":
    sys.exit(main())
