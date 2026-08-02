#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import parse_aws


@dataclass(frozen=True)
class GlacierVault:
    vault_name: str
    size_in_bytes: float = 0
    number_of_archives: float = 0
    tagging: Mapping[str, str] | None = None


Section = Mapping[str, GlacierVault]

Params = Mapping[str, tuple[float | None, ...] | None]


def parse_aws_glacier(string_table: StringTable) -> Section:
    parsed_by_vault: dict[str, GlacierVault] = {}
    for vault in parse_aws(string_table):
        parsed_by_vault[vault["VaultName"]] = GlacierVault(
            vault_name=vault["VaultName"],
            size_in_bytes=vault.get("SizeInBytes", 0),
            number_of_archives=vault.get("NumberOfArchives", 0),
            tagging=vault.get("Tagging"),
        )
    return parsed_by_vault


def _vault_size_levels(params: Params) -> LevelsT[float]:
    # The ruleset still stores the legacy levels format: either a (warn, crit)
    # tuple or a tuple consisting solely of `None`s ("no levels").
    match params.get("vault_size_levels"):
        case (float() | int() as warn, float() | int() as crit):
            return ("fixed", (warn, crit))
        case _:
            return ("no_levels", None)


# .
#   .--Glacier archives----------------------------------------------------.
#   |                    ____ _            _                               |
#   |                   / ___| | __ _  ___(_) ___ _ __                     |
#   |                  | |  _| |/ _` |/ __| |/ _ \ '__|                    |
#   |                  | |_| | | (_| | (__| |  __/ |                       |
#   |                   \____|_|\__,_|\___|_|\___|_|                       |
#   |                               _     _                                |
#   |                 __ _ _ __ ___| |__ (_)_   _____  ___                 |
#   |                / _` | '__/ __| '_ \| \ \ / / _ \/ __|                |
#   |               | (_| | | | (__| | | | |\ V /  __/\__ \                |
#   |                \__,_|_|  \___|_| |_|_| \_/ \___||___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_aws_glacier(section: Section) -> DiscoveryResult:
    for vault_name in section:
        yield Service(item=vault_name)


def check_aws_glacier_archives(item: str, params: Params, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    yield from check_levels(
        data.size_in_bytes,
        metric_name="aws_glacier_vault_size",
        levels_upper=_vault_size_levels(params),
        render_func=render.disksize,
        label="Vault size",
    )

    num_archives = data.number_of_archives
    yield Result(state=State.OK, summary=f"Number of archives: {int(num_archives)}")
    yield Metric("aws_glacier_num_archives", num_archives)

    if tag_infos := [f"{key}: {value}" for key, value in (data.tagging or {}).items()]:
        yield Result(state=State.OK, summary=f"[Tags]: {', '.join(tag_infos)}")


agent_section_aws_glacier = AgentSection(
    name="aws_glacier",
    parse_function=parse_aws_glacier,
)


check_plugin_aws_glacier = CheckPlugin(
    name="aws_glacier",
    service_name="AWS/Glacier Vault: %s",
    discovery_function=discover_aws_glacier,
    check_function=check_aws_glacier_archives,
    check_ruleset_name="aws_glacier_vault_archives",
    check_default_parameters={},
)

# .
#   .--Glacier summary-----------------------------------------------------.
#   |                    ____ _            _                               |
#   |                   / ___| | __ _  ___(_) ___ _ __                     |
#   |                  | |  _| |/ _` |/ __| |/ _ \ '__|                    |
#   |                  | |_| | | (_| | (__| |  __/ |                       |
#   |                   \____|_|\__,_|\___|_|\___|_|                       |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   '----------------------------------------------------------------------


def discover_aws_glacier_summary(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_glacier_summary(params: Params, section: Section) -> CheckResult:
    sum_size = 0.0
    largest_vault = None
    largest_vault_size = 0.0
    for vault_name in sorted(section):
        vault_size = section[vault_name].size_in_bytes
        sum_size += vault_size
        if vault_size >= largest_vault_size:
            largest_vault = vault_name
            largest_vault_size = vault_size

    yield from check_levels(
        sum_size,
        metric_name="aws_glacier_total_vault_size",
        levels_upper=_vault_size_levels(params),
        render_func=render.disksize,
        label="Total size",
    )

    if largest_vault:
        yield Result(
            state=State.OK,
            summary=f"Largest vault: {largest_vault} ({render.disksize(largest_vault_size)})",
        )
        yield Metric("aws_glacier_largest_vault_size", largest_vault_size)


check_plugin_aws_glacier_summary = CheckPlugin(
    name="aws_glacier_summary",
    service_name="AWS/Glacier Summary",
    sections=["aws_glacier"],
    discovery_function=discover_aws_glacier_summary,
    check_function=check_aws_glacier_summary,
    check_ruleset_name="aws_glacier_vaults",
    check_default_parameters={},
)
