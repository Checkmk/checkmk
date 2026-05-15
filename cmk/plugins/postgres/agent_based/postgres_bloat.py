#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.postgres import lib as postgres

# <<<postgres_bloat>>>
# [databases_start]
# postgres
# testdb
# datenbank
# [databases_end]
# db;schemaname;tablename;tups;pages;otta;tbloat;wastedpages;wastedbytes;wastedsize;iname;itups;ipages;iotta;ibloat;wastedipages;wastedibytes;wastedisize;totalwastedbytes
# postgres;pg_catalog;pg_amop;403;4;3;1.3;1;8192;8192;pg_amop_oid_index;403;4;2;2.0;2;16384;16384;24576
# postgres;pg_catalog;pg_amproc;291;3;2;1.5;1;8192;8192;pg_amproc_fam_proc_index;291;4;2;2.0;2;16384;16384;24576
# postgres;pg_catalog;pg_amop;403;4;3;1.3;1;8192;8192;pg_amop_opr_fam_index;403;4;2;2.0;2;16384;16384;24576

# instances
# <<<postgres_bloat>>>
# [[[foobar]]]
# [databases_start]
# postgres
# testdb
# [databases_end]
# ...


def discover_postgres_bloat(section: postgres.Section) -> DiscoveryResult:
    for entry, values in section.items():
        if values:
            yield Service(item=entry)


def check_postgres_bloat(
    item: str, params: Mapping[str, Any], section: postgres.Section
) -> CheckResult:
    database = section.get(item)
    if not database:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    table_perc_max: Mapping[str, str] | None = None
    table_abs_max: Mapping[str, str] | None = None
    index_perc_max: Mapping[str, str] | None = None
    index_abs_max: Mapping[str, str] | None = None

    table_abs_total = 0
    index_abs_total = 0

    show_levels = False
    for line in database:
        tbloat = float(line["tbloat"])
        twasted = int(line["wastedbytes"])
        ibloat = float(line["ibloat"])
        iwasted = int(line["wastedibytes"])

        table_abs_total += twasted
        index_abs_total += iwasted

        # Calculate highest loss
        if not table_perc_max or tbloat > float(table_perc_max["tbloat"]):
            table_perc_max = line
        if not table_abs_max or twasted > int(table_abs_max["wastedbytes"]):
            table_abs_max = line
        if not index_perc_max or ibloat > float(index_perc_max["ibloat"]):
            index_perc_max = line
        if not index_abs_max or iwasted > int(index_abs_max["wastedibytes"]):
            index_abs_max = line

        for what, bloat, wasted in [("table", tbloat, twasted), ("index", ibloat, iwasted)]:
            if f"{what}_bloat_perc" in params:
                warn, crit = params[f"{what}_bloat_perc"]
                if bloat >= crit:
                    yield Result(
                        state=State.CRIT,
                        summary=f"{line['tablename']} {what} bloat: {bloat}% (too high)",
                    )
                    show_levels = True
                elif bloat >= warn:
                    yield Result(
                        state=State.WARN,
                        summary=f"{line['tablename']} {what} bloat: {bloat}% (too high)",
                    )
                    show_levels = True

            if f"{what}_bloat_abs" in params:
                warn, crit = params[f"{what}_bloat_abs"]
                if wasted >= crit:
                    yield Result(
                        state=State.CRIT,
                        summary=(
                            f"{line['tablename']} wasted {what} bytes: "
                            f"{render.bytes(wasted)} (too high)"
                        ),
                    )
                    show_levels = True
                elif wasted >= warn:
                    yield Result(
                        state=State.WARN,
                        summary=(
                            f"{line['tablename']} wasted {what} bytes: "
                            f"{render.bytes(wasted)} (too high)"
                        ),
                    )
                    show_levels = True

    if show_levels:
        levels_info = ["Levels:"]
        for what in ["table", "index"]:
            if f"{what}_bloat_perc" in params:
                warn, crit = params[f"{what}_bloat_perc"]
                levels_info.append(f"{what.title()} Perc ({warn:.0f}%/{crit:.0f}%)")
            if f"{what}_bloat_abs" in params:
                warn, crit = params[f"{what}_bloat_abs"]
                levels_info.append(
                    f"{what.title()} Abs ({render.bytes(int(warn))}/{render.bytes(int(crit))})"
                )
        yield Result(state=State.OK, summary=" ".join(levels_info))
    else:
        # No errors. Show some general information
        for what, perc_max, abs_max in [
            ("table", table_perc_max, table_abs_max),
            ("index", index_perc_max, index_abs_max),
        ]:
            assert perc_max is not None and abs_max is not None
            yield Result(
                state=State.OK,
                summary=(
                    f"Maximum {what} bloat at {perc_max['tablename']}: "
                    f"{render.percent(float(perc_max[f'{what[0]}bloat']))}"
                ),
            )
            wasted_key = "wastedibytes" if what == "index" else "wastedbytes"
            yield Result(
                state=State.OK,
                summary=(
                    f"Maximum wasted {what}space at {abs_max['tablename']}: "
                    f"{render.bytes(int(abs_max[wasted_key]))}"
                ),
            )

    # Summary information
    for what, total_value in [("table", table_abs_total), ("index", index_abs_total)]:
        yield Result(
            state=State.OK,
            summary=f"Summary of top {len(database)} wasted {what}space: {render.bytes(total_value)}",
        )
        yield Metric(f"{what}space_wasted", total_value)


agent_section_postgres_bloat = AgentSection(
    name="postgres_bloat",
    parse_function=postgres.parse_dbs,
)


check_plugin_postgres_bloat = CheckPlugin(
    name="postgres_bloat",
    service_name="PostgreSQL Bloat %s",
    discovery_function=discover_postgres_bloat,
    check_function=check_postgres_bloat,
    check_ruleset_name="db_bloat",
    check_default_parameters={
        "table_bloat_perc": (180.0, 200.0),  # WARN at 180%, CRIT at 200%
        "index_bloat_perc": (180.0, 200.0),
    },
)
