#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from cmk.agent_based.v2 import Result, State, StringTable


# This function must be executed for each agent line which has been
# found for the current item. It must deal with the ORA-* error
# messages. It has to skip over the lines which show the SQL statement
# and the SQL error message which comes before the ORA-* message.
#
# The check must completely skip the lines before the ORA-* messages
# and return UNKNOWN on the first found ORA-* message.
# line[0] is the item (db instance)
#
# This function returns a tuple when an ORA-* message has been found.
# It returns False if this line should be skipped by the check.
def oracle_handle_ora_errors(line: Sequence[str]) -> Result | Literal[False] | None:
    if len(line) == 1:
        return None

    legacy_error = _oracle_handle_legacy_ora_errors(line)
    if legacy_error:
        return legacy_error

    # Handle error output from new agent
    if line[1] == "FAILURE":
        if len(line) >= 3 and line[2].startswith("ORA-"):
            return Result(state=State.UNKNOWN, summary="%s" % " ".join(line[2:]))
        return False  # ignore other FAILURE lines

    # Handle error output from old (pre 1.2.0p2) agent
    if line[1] in ["select", "*", "ERROR"]:
        return False
    if line[1].startswith("ORA-"):
        return Result(
            state=State.UNKNOWN, summary='Found error in agent output "%s"' % " ".join(line[1:])
        )
    return None


def _oracle_handle_legacy_ora_errors(line: Sequence[str]) -> Result | Literal[False] | None:
    # Skip over line before ORA- errors (e.g. sent by AIX agent from 2014)
    if line == ["ERROR:"]:
        return False

    if line[0].startswith("ORA-"):
        return Result(
            state=State.UNKNOWN, summary='Found error in agent output "%s"' % " ".join(line)
        )

    # Handle error output from 1.6 solaris agent, see SUP-9521
    if line[0] == "Error":
        return Result(
            state=State.UNKNOWN, summary='Found error in agent output "%s"' % " ".join(line[1:])
        )
    return None


# Fully prevent creation of services when an error is found.
def oracle_handle_ora_errors_discovery(info: StringTable) -> None:
    for line in info:
        err = oracle_handle_ora_errors(line)
        if err is False:
            continue
        if isinstance(err, tuple):
            raise RuntimeError(err[1])  # soooo ... we create a crash report?
