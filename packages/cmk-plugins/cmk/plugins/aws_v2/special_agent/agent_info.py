#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The aws_v2_agent_info section: what one run reached, written to the rule host.

Every run writes it, also when nothing failed, so that its service exists before the
first error. Each line is one JSON object: a row about one account, or, without an
account, about the run as a whole.

An account is "ok" once the agent reached it, that is, once the login and its role
worked. Sections that fail inside a reached account are reported in aws_v2_exceptions
on the account's host.
"""

import json
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class AgentInfoRow:
    status: Literal["ok", "error"]
    account: str | None = None
    reason: str | None = None

    def to_json(self) -> str:
        return json.dumps({key: value for key, value in asdict(self).items() if value is not None})


def write_agent_info(rows: Iterable[AgentInfoRow]) -> None:
    sys.stdout.write("<<<aws_v2_agent_info:sep(0)>>>\n")
    for row in rows:
        sys.stdout.write(f"{row.to_json()}\n")
