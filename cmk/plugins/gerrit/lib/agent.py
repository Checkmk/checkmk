#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import pathlib
import sys
from collections.abc import Sequence

from cmk.utils import password_store

from cmk.plugins.gerrit.lib import collectors
from cmk.plugins.gerrit.lib.shared_typing import Sections
from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser


def main() -> int:
    return special_agent_main(parse_arguments, run_agent)


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = create_default_argument_parser(description=__doc__)

    parser.add_argument("-u", "--user", default="", help="Username for Gerrit login")
    group_password = parser.add_mutually_exclusive_group(required=True)
    group_password.add_argument(
        "--password-ref",
        help="Password store reference to the secret password for your Gerrit account.",
    )
    group_password.add_argument("-s", "--password", help="Password for Gerrit login")
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


def run_agent(args: Args) -> int:
    api_url = f"{args.proto}://{args.hostname}:{args.port}/a"
    auth = (args.user, get_password_from_args(args))

    sections: Sections = {}

    version_collector = collectors.GerritVersion(api_url=api_url, auth=auth)
    sections.update(version_collector.collect())

    write_sections(sections)

    return 0


def get_password_from_args(args: Args) -> str:
    if args.password:
        return args.password

    pw_id, pw_file = args.password_ref.split(":", maxsplit=1)

    return password_store.lookup(pathlib.Path(pw_file), pw_id)


def write_sections(sections: Sections) -> None:
    for name, data in sections.items():
        with SectionWriter(f"gerrit_{name}") as writer:
            writer.append_json(data)


if __name__ == "__main__":
    sys.exit(main())
