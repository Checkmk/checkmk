#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

# <<<oracle_sql:sep(58)>>>
# [[[SID-1|SQL-A|cached(123,456)]]]
# details:DETAILS
# perfdata:NAME=VAL;WARN;CRIT;MIN;MAX NAME=VAL;WARN;CRIT;MIN;MAX ...
# perfdata:NAME=VAL;WARN;CRIT;MIN;MAX ...
# long:LONG
# long:LONG
# ...
# exit:CODE
# elapsed:TS
# [[[SID-2|SQL-B]]]
# details:DETAILS
# perfdata:
# long:LONG
# long:LONG
# ...
# exit:CODE
# elapsed:TS
# mypy: disable-error-code="var-annotated"
from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.plugins.lib.cache_helper import CacheInfo, render_cache_info


def _prepare_instance(line: str, now: float) -> tuple[str, str, dict]:
    sid, item, *rest = line.split("|")
    instance = {
        "details": [],
        "perfdata": [],
        "long": [],
        "exit": 0,
        "elapsed": None,
        "parsing_error": {},
        "cache_info": None,
    }
    if rest:
        instance["cache_info"] = CacheInfo.from_raw(rest[0], now)
    return sid, item, instance


def parse_oracle_sql(string_table):
    def parse_perfdata(line):
        perfdata = []
        for entry in line.split():
            if not entry:
                continue
            var_name, data_str = entry.split("=", 1)
            perf_entry = [var_name]
            for data_entry in data_str.split(";"):
                try:
                    perf_entry.append(float(data_entry) if "." in data_entry else int(data_entry))
                except Exception:
                    perf_entry.append(None)
            perfdata.append(tuple(perf_entry))
        return perfdata

    now = time.time()
    parsed = {}
    instance = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            sid, item, inst = _prepare_instance(line[0][3:-3], now)
            instance = parsed.setdefault((f"{sid} SQL {item}").upper(), inst)
            continue

        if instance is None:
            continue

        key = line[0]
        infotext = ":".join(line[1:]).strip()
        if key.endswith("ERROR") or key.startswith("ERROR at line") or "|FAILURE|" in key:
            instance["parsing_error"].setdefault(("instance", "PL/SQL failure", 2), []).append(
                "{}: {}".format(key.split("|")[-1], infotext)
            )

        elif key in ["details", "long"]:
            instance[key].append(infotext)

        elif key == "perfdata":
            try:
                instance[key] += parse_perfdata(line[1])
            except Exception:
                instance["parsing_error"].setdefault(("perfdata", "Perfdata error", 3), []).append(
                    infotext
                )

        elif key == "exit":
            instance[key] = int(line[1])

        elif key == "elapsed":
            if line[1] != "":
                instance[key] = float(line[1])

        else:
            instance["parsing_error"].setdefault(
                ("unknown", f'Unexpected Keyword: "{key}". Line was', 3), []
            ).append(":".join(line).strip())

    return parsed


def inventory_oracle_sql(parsed):
    for instance in parsed:
        yield instance, {}


def check_oracle_sql(item, params, parsed):
    if item not in parsed:
        return

    data = parsed[item]
    for (error_key, error_title, error_state), error_lines in data["parsing_error"].items():
        error_state = params.get("%s_error_state" % error_key, error_state)
        yield error_state, "{}: {}".format(error_title, " ".join(error_lines))

    perfdata = data["perfdata"]
    elapsed_time = data["elapsed"]
    if elapsed_time is not None:
        perfdata.append(("elapsed_time", elapsed_time))

    if details := data["details"]:
        yield data["exit"], ", ".join(details), perfdata

    if long := data["long"]:
        yield 0, "\n%s" % "\n".join(long)

    if cache_info := data["cache_info"]:
        yield 0, render_cache_info(cache_info)


check_info["oracle_sql"] = LegacyCheckDefinition(
    parse_function=parse_oracle_sql,
    service_name="ORA %s",
    discovery_function=inventory_oracle_sql,
    check_function=check_oracle_sql,
    check_ruleset_name="oracle_sql",
)
