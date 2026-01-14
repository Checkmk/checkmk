#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

check_info = {}

# <<<db2_bp_hitratios>>>
# [[[db2taddm:CMDBS1]]]
# BP_NAME        TOTAL_HIT_RATIO_PERCENT DATA_HIT_RATIO_PERCENT INDEX_HIT_RATIO_PERCENT XDA_HIT_RATIO_PERCENT
# IBMDEFAULTBP                     99.36                  98.48                   99.94                     -
# BUF8K                            99.94                  99.94                   99.95                     -
# BUF32K                           99.99                  99.98                   99.99                     -
# BP8                             100.00                 100.00                       -                     -


def parse_db2_bp_hitratios(string_table):
    pre_parsed = parse_db2_dbs(string_table)

    # Some databases run in DPF mode. This means they are split over several instances
    # Each instance has its own bufferpool hitratio information. We create on service for each instance
    databases = {}
    for instance, lines in pre_parsed[1].items():
        header_idx, node_names = None, []
        for idx, line in enumerate(lines):
            if line[0] == "node":
                node_names.append(" ".join(line[1:]))
            elif line[0] == "BP_NAME":
                header_idx = idx
                node_headers = line
                break

        if node_names:
            if header_idx is None:
                continue
            # DPF mode
            current_node_offset = -1
            current_instance = None
            for line in lines[header_idx + 1 :]:
                if line[0] == "IBMDEFAULTBP":
                    current_node_offset += 1
                    current_instance = f"{instance} DPF {node_names[current_node_offset]}"
                    databases.setdefault(current_instance, [node_headers])
                if current_instance in databases:
                    databases[current_instance].append(line)
        else:
            databases[instance] = lines

    return databases


def discover_db2_bp_hitratios(parsed):
    for key, values in parsed.items():
        for field in values[1:]:
            if not field[0].startswith("IBMSYSTEMBP"):
                yield f"{key}:{field[0]}", {}


def check_db2_bp_hitratios(item, _no_params, parsed):
    db_instance, field = item.rsplit(":", 1)
    db = parsed.get(db_instance)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    headers = db[0]
    for line in db[1:]:
        if field == line[0]:
            hr_info = dict(zip(headers[1:], line[1:]))  # skip BP_NAME
            for key in headers[1:]:
                value = hr_info[key]
                value = value.replace("-", "0").replace(",", ".")
                key = key.replace("_RATIO_PERCENT", "")
                map_key_to_text = {
                    "TOTAL_HIT": "Total",
                    "DATA_HIT": "Data",
                    "INDEX_HIT": "Index",
                    "XDA_HIT": "XDA",
                }
                yield (
                    0,
                    f"{map_key_to_text[key]}: {value}%",
                    [("%sratio" % key.lower(), float(value), None, None, 0, 100)],
                )
            break


check_info["db2_bp_hitratios"] = LegacyCheckDefinition(
    name="db2_bp_hitratios",
    parse_function=parse_db2_bp_hitratios,
    service_name="DB2 BP-Hitratios %s",
    discovery_function=discover_db2_bp_hitratios,
    check_function=check_db2_bp_hitratios,
)
