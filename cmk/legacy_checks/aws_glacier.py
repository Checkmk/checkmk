#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable
from cmk.plugins.aws.lib import parse_aws

check_info = {}


@dataclass(frozen=True)
class GlacierVault:
    vault_name: str
    size_in_bytes: float = 0
    number_of_archives: float = 0
    tagging: Mapping[str, str] | None = None


Section = Mapping[str, GlacierVault]


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


def discover_aws_glacier(parsed: Section):
    for vault_name in parsed:
        yield vault_name, {}


def check_aws_glacier_archives(item, params, parsed: Section):
    if (data := parsed.get(item)) is None:
        return
    vault_size = data.size_in_bytes
    yield check_levels(
        vault_size,
        "aws_glacier_vault_size",
        params.get("vault_size_levels", (None, None)),
        human_readable_func=render.disksize,
        infoname="Vault size",
    )

    num_archives = data.number_of_archives
    yield (
        0,
        "Number of archives: %s" % int(num_archives),
        [("aws_glacier_num_archives", num_archives)],
    )

    tag_infos = []
    for key, value in list((data.tagging or {}).items()):
        tag_infos.append(f"{key}: {value}")
    if tag_infos:
        yield 0, "[Tags]: %s" % ", ".join(tag_infos)


check_info["aws_glacier"] = LegacyCheckDefinition(
    name="aws_glacier",
    parse_function=parse_aws_glacier,
    service_name="AWS/Glacier Vault: %s",
    discovery_function=discover_aws_glacier,
    check_function=check_aws_glacier_archives,
    check_ruleset_name="aws_glacier_vault_archives",
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


def discover_aws_glacier_summary(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_aws_glacier_summary(item, params, parsed: Section):
    sum_size = 0.0
    largest_vault = None
    largest_vault_size = 0.0
    for vault_name in sorted(parsed):
        vault_size = parsed[vault_name].size_in_bytes
        sum_size += vault_size
        if vault_size >= largest_vault_size:
            largest_vault = vault_name
            largest_vault_size = vault_size
    yield check_levels(
        sum_size,
        "aws_glacier_total_vault_size",
        params.get("vault_size_levels", (None, None)),
        human_readable_func=render.disksize,
        infoname="Total size",
    )

    if largest_vault:
        yield (
            0,
            f"Largest vault: {largest_vault} ({render.disksize(largest_vault_size)})",
            [("aws_glacier_largest_vault_size", largest_vault_size)],
        )


check_info["aws_glacier.summary"] = LegacyCheckDefinition(
    name="aws_glacier_summary",
    service_name="AWS/Glacier Summary",
    sections=["aws_glacier"],
    discovery_function=discover_aws_glacier_summary,
    check_function=check_aws_glacier_summary,
    check_ruleset_name="aws_glacier_vaults",
)
