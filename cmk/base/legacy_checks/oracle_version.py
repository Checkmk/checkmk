#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.oracle import (
    oracle_handle_ora_errors,
    oracle_handle_ora_errors_discovery,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}

# <<<oracle_version>>>
# XE Oracle Database 11g Express Edition Release 11.2.0.2.0 - 64bit Production


def inventory_oracle_version(info):
    oracle_handle_ora_errors_discovery(info)
    return [(line[0], None) for line in info if len(line) >= 2]


def check_oracle_version(item, _no_params, info):
    for line in info:
        if line[0] == item:
            err = oracle_handle_ora_errors(line)
            if err is False:
                continue
            if isinstance(err, tuple):
                return err

            return (0, "Version: " + " ".join(line[1:]))
    return (3, "no version information, database might be stopped")


def parse_oracle_version(string_table: StringTable) -> StringTable:
    return string_table


check_info["oracle_version"] = LegacyCheckDefinition(
    name="oracle_version",
    parse_function=parse_oracle_version,
    service_name="ORA Version %s",
    discovery_function=inventory_oracle_version,
    check_function=check_oracle_version,
)
