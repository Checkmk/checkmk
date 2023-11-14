#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to migrate from agent based API v1 to v2.

This script automates the most common changes required to migrate
a plugin developed against the agent based API v1 to the API version 2.

Note that it is not perfect.
You have to check and adjust the result manually!
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

IMPORTS = (
    ("cmk.base.plugins.agent_based.agent_based_api.v1", "cmk.agent_based.v2"),
    (".agent_based_api.v1", "cmk.agent_based.v2"),
    ("cmk.base.plugins.agent_based.utils", ".utils"),
)


REGISTRATION_REGEXES = (
    (
        "agent_section",
        "AgentSection",
        re.compile(r'register\.agent_section(.*?\ name="([^"]*).*?\))$', re.DOTALL),
    ),
    (
        "snmp_section",
        "SimpleSNMPSection",
        re.compile(r'register\.snmp_section(.*?\ name="([^"]*).*?fetch=SNMP.*?\))$', re.DOTALL),
    ),
    (
        "snmp_section",
        "SNMPSection",
        re.compile(r'register\.snmp_section(.*?\ name="([^"]*).*?fetch=\[.*?\))$', re.DOTALL),
    ),
    (
        "check_plugin",
        "CheckPlugin",
        re.compile(r'register\.check_plugin(.*?\ name="([^"]*).*?\))$', re.DOTALL),
    ),
    (
        "inventory_plugin",
        "InventoryPlugin",
        re.compile(r'register\.inventory_plugin(.*?\ name="([^"]*).*?\))$', re.DOTALL),
    ),
)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "-i", "--inplace", action="store_true", help="Modify the passed files in place."
    )
    parser.add_argument(
        "file_name",
        type=Path,
        nargs="+",
        help="The file(s) to operate on.",
    )

    return parser.parse_args(argv)


def _transform(file_name: Path, inplace: bool) -> None:
    content = file_name.read_text()

    marker = "\nfrom" if "\nfrom" in content else "\nimport"
    content = content.replace(
        marker,
        (
            "\nfrom cmk.agent_based.v2 import AgentSection, SNMPSection,"
            f" SimpleSNMPSection, CheckPlugin, InvetoryPlugin{marker}"
        ),
        1,
    )

    for old, new in IMPORTS:
        content = content.replace(old, new)

    for prefix, plugin, regex in REGISTRATION_REGEXES:
        while (m := next(regex.finditer(content), None)) is not None:
            content = content.replace(m.group(0), f"{prefix}_{m.group(2)} = {plugin}{m.group(1)}")

    if inplace:
        file_name.write_text(content)
    else:
        sys.stdout.write(content)


def _autoflake(file_names: Sequence[str]) -> None:
    subprocess.check_call(["autoflake", "-i", "--remove-all-unused-imports", *file_names])


def main(argv: list[str]) -> int:
    args = parse_arguments(argv)
    for file_name in args.file_name:
        _transform(file_name, args.inplace)

    _autoflake(args.file_name)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
