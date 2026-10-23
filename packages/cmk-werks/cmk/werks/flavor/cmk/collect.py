#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator

BRANCH_REGEX = r"^master$|^\d+\.\d+\.\d+"


def cleanup_branch_name(branch_name: str) -> str:
    """
    >>> cleanup_branch_name("1.5.0i3")
    '1.5.0'

    >>> cleanup_branch_name("1.5.0")
    '1.5.0'

    >>> [cleanup_branch_name(v) for v in [ "1.2.5", "1.2.6", "1.2.7", "1.2.8"]]
    ['1.2.0', '1.2.0', '1.2.0', '1.2.0']
    """
    if branch_name.startswith("1.2."):
        return "1.2.0"
    return re.sub(r"(i\d+)$", "", branch_name)


def adapt_werk_string(werk_string: str, werk_id: int) -> str:
    if werk_id == 1281:
        # werk 1281 of cmk is missing a newline, but it is available in
        # multiple branches so we fix it here
        return werk_string.replace("Class: feature", "Class: feature\n")
    if werk_id == 3229:
        # don't want to commit to branch 1.2.8
        return werk_string.replace("name inventorized\\", "name inventorized")
    if werk_id in {1071, 198, 4045, 10589, 7032, 10579}:
        return _replace_compatible(werk_string, "compat")
    if werk_id in {4914, 4737, 10303, 11202, 11277, 7048, 11159, 11475}:
        return _replace_compatible(werk_string, "incomp")
    if werk_id == 13164:
        return werk_string.replace("<PC_NAME>", "&lt;PC_NAME>")
    if werk_id == 13488:
        return werk_string.replace("<tt>postgres_conn_time</tt>:", "postgres_conn_time:")
    if werk_id == 5141:
        return werk_string.replace("parameter <tt>request_format</tt>", "parameter request_format")
    return werk_string


COMP_MATCHER = re.compile("^Compatible: (comp|multisite|incompat|imcompat|compa)$")


def _replace_compatible(werk_string: str, compatible: str) -> str:
    def generator() -> Iterator[str]:
        for line in werk_string.split("\n"):
            if COMP_MATCHER.match(line):
                line = f"Compatible: {compatible}"
            yield line
            yield "\n"

    return "".join(generator())
