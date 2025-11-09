#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import argparse
import json
import pathlib
import sys
from collections.abc import Sequence

from cmk.plugins.gerrit.lib import collectors, storage
from cmk.plugins.gerrit.lib.shared_typing import Sections
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace
from cmk.utils.password_store import lookup as password_store_lookup

__version__ = "2.5.0b1"

AGENT = "gerrit"


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    return run_agent(parse_arguments(sys.argv[1:]))


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
    group_password = parser.add_mutually_exclusive_group(required=True)
    group_password.add_argument(
        "--password-ref",
        help="Password store reference to the secret password for your Gerrit account.",
    )
    group_password.add_argument("-s", "--password", help="Password for Gerrit login")
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


def run_agent(args: argparse.Namespace) -> int:
    api_url = f"{args.proto}://{args.hostname}:{args.port}/a"
    auth = (args.user, get_password_from_args(args))

    sections: Sections = {}

    version_collector = collectors.GerritVersion(api_url=api_url, auth=auth)
    version_cache = storage.VersionCache(collector=version_collector, interval=args.version_cache)
    sections.update(version_cache.get_sections())

    write_sections(sections)

    return 0


def get_password_from_args(args: argparse.Namespace) -> str:
    if args.password:
        return args.password

    pw_id, pw_file = args.password_ref.split(":", maxsplit=1)

    return password_store_lookup(pathlib.Path(pw_file), pw_id)


def write_sections(sections: Sections) -> None:
    for name, data in sections.items():
        section_payload = json.dumps(data, sort_keys=True)
        sys.stdout.write(f"<<<gerrit_{name}:sep(0)>>>\n{section_payload}\n")


if __name__ == "__main__":
    sys.exit(main())
