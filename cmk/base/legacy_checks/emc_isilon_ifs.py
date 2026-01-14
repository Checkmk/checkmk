#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.df import FSBlock

check_info = {}


def discover_emc_isilon_ifs(section: FSBlock) -> list[tuple[str, None]]:
    return [("Cluster", None)]


def check_emc_isilon_ifs(item: str, params: Mapping[str, Any], section: FSBlock) -> Iterable:
    return df_check_filesystem_list("ifs", params, [section])


check_info["emc_isilon_ifs"] = LegacyCheckDefinition(
    name="emc_isilon_ifs",
    service_name="Filesystem %s",
    # section already migrated
    discovery_function=discover_emc_isilon_ifs,
    check_function=check_emc_isilon_ifs,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
