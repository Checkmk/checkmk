#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    Result,
    State,
    StringTable,
)
from cmk.agent_based.v3_unstable import discover_one_service


class AgentInfoRow(BaseModel, frozen=True):
    status: Literal["ok", "error", "info"]
    account: str | None = None
    reason: str | None = None
    region: str | None = None


Section = Sequence[AgentInfoRow]


def parse_aws_agent_info(string_table: StringTable) -> Section:
    return [AgentInfoRow.model_validate_json(line[0]) for line in string_table]


def _place(row: AgentInfoRow) -> str:
    account = f"Account {row.account}" if row.account else None
    return ", ".join(part for part in (account, row.region) if part)


def check_aws_agent_info(section: Section) -> CheckResult:
    reached = sum(row.status == "ok" for row in section)
    yield Result(state=State.OK, summary=f"Accounts reached: {reached}")

    for row in section:
        if row.status != "error":
            continue
        if row.account is None:
            yield Result(state=State.CRIT, summary=row.reason or "The agent run failed")
        else:
            yield Result(
                state=State.CRIT,
                summary=f"Account {row.account} unreachable",
                details=row.reason,
            )

    for row in section:
        if row.status == "info":
            yield Result(state=State.OK, notice=f"{_place(row)}: {row.reason}")


agent_section_aws_v2_agent_info = AgentSection(
    name="aws_v2_agent_info",
    parse_function=parse_aws_agent_info,
)

check_plugin_aws_v2_agent_info = CheckPlugin(
    name="aws_v2_agent_info",
    service_name="AWS agent info",
    discovery_function=discover_one_service,
    check_function=check_aws_agent_info,
)
