#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to migrate from agent based API v1 to v2.

This script automates the most common changes required to migrate
a plugin developed against the agent based API v1 to the API version 2.

Files are changed inplace.

Note that it is not perfect.
You have to check and adjust the result manually!
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Self

IMPORT_REPLACEMENTS = (
    ("from .agent_based_api.v1 import check_levels\n", "\n"),
    ("from cmk.base.plugins.agent_based_api.v1 import check_levels\n", "\n"),
    ("check_levels,", ""),
    (", check_levels", ""),
    ("cmk.base.plugins.agent_based.agent_based_api.v1", "cmk.agent_based.v2"),
    (".agent_based_api.v1", "cmk.agent_based.v2"),
    ("cmk.base.plugins.agent_based.utils", ".utils"),
    ("cmk.agent_based.v2.type_defs", "cmk.agent_based.v2"),
    ("register,", ""),
    (", register", ""),
    ("type_defs,", ""),
    (", type_defs", ""),
)


IMPORTS_ADDED = (
    "from collections.abc import Sequence\n"
    "from cmk.agent_based.v1 import check_levels\n"
    "from cmk.agent_based.v2 import AgentSection, SNMPSection,"
    " SimpleSNMPSection, CheckPlugin, InventoryPlugin, RuleSetType,"
    " CheckResult, DiscoveryResult, StringTable, get_value_store, StringByteTable"
    "\n\n"
)

REGISTRATION_REGEXES = (
    (
        "agent_section",
        "AgentSection",
        re.compile(r'register\.agent_section(.*?name="([^"]*).*?\))$', re.DOTALL),
    ),
    (
        "snmp_section",
        "SimpleSNMPSection",
        re.compile(r'register\.snmp_section(.*?name="([^"]*).*?fetch=SNMP.*?\))$', re.DOTALL),
    ),
    (
        "snmp_section",
        "SNMPSection",
        re.compile(r'register\.snmp_section(.*?name="([^"]*).*?fetch=\[.*?\))$', re.DOTALL),
    ),
    (
        "check_plugin",
        "CheckPlugin",
        re.compile(r'register\.check_plugin(.*?name="([^"]*).*?\))$', re.DOTALL),
    ),
    (
        "inventory_plugin",
        "InventoryPlugin",
        re.compile(r'register\.inventory_plugin(.*?name="([^"]*).*?\))$', re.DOTALL),
    ),
)

BODY_REPLACEMENTS = (
    ("list[StringTable]", "Sequence[StringTable]"),
    ("type_defs.", ""),
    ("register.RuleSetType", "RuleSetType"),
)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("-d", "--debug", action="store_true", help="Raise exceptions.")
    parser.add_argument("files", type=Path, nargs="+", help="The file(s) to operate on.")

    return parser.parse_args(argv)


@dataclass
class PyFile:
    header: str
    imports: str
    body: str

    def __str__(self) -> str:
        return self.header + self.imports + self.body

    @classmethod
    def from_content(cls, content: str) -> Self:
        header, imports, body = [], [], []
        ilines = iter(content.splitlines())

        for line in ilines:
            if not line.startswith(("import", "from")):
                header.append(f"{line}\n")
            else:
                imports.append(f"{line}\n")
                break

        for line in ilines:
            if line.startswith(("import", "from", "    ", ")")) or not line:
                imports.append(f"{line}\n")
            else:
                body.append(f"{line}\n")
                break

        body.extend(f"{line}\n" for line in ilines)
        return cls("".join(header), "".join(imports), "".join(body))


def _transform(file_name: Path) -> None:
    py_file = PyFile.from_content(file_name.read_text())

    py_file.imports = _transform_imports(py_file.imports)
    py_file.body = _transform_body(py_file.body)

    file_name.write_text(str(py_file))


def _transform_imports(imports: str) -> str:
    for old, new in IMPORT_REPLACEMENTS:
        imports = imports.replace(old, new)
    return imports + IMPORTS_ADDED


def _transform_body(body: str) -> str:
    for prefix, plugin, regex in REGISTRATION_REGEXES:
        while (m := next(regex.finditer(body), None)) is not None:
            body = body.replace(m.group(0), f"{prefix}_{m.group(2)} = {plugin}{m.group(1)}")

    for old, new in BODY_REPLACEMENTS:
        body = body.replace(old, new)
    return body


def _try_to_run(*command_items: object) -> None:
    try:
        subprocess.check_call([str(o) for o in command_items])
    except subprocess.CalledProcessError as exc:
        print(f"tried to run {command_items[0]!r}, but: {exc}", file=sys.stderr)


def main(argv: list[str]) -> int:
    args = parse_arguments(argv)
    for file_name in args.files:
        try:
            _transform(file_name)
        except Exception as e:
            if args.debug:
                raise
            sys.stderr.write(f"ERROR {file_name}: {e}\n")

    _try_to_run("scripts/run-sort", *args.files)
    _try_to_run("autoflake", "-i", "--remove-all-unused-imports", *args.files)
    _try_to_run("scripts/run-format", *args.files)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
