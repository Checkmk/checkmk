#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="index"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render
from cmk.plugins.postgres import lib as postgres

check_info = {}

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


def discover_postgres_bloat(parsed):
    return [(entry, {}) for entry, values in parsed.items() if values]


def check_postgres_bloat(item, params, parsed):
    database = parsed.get(item)
    if not database:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    table_perc_max = None
    table_abs_max = None
    index_perc_max = None
    index_abs_max = None

    table_abs_total = 0
    index_abs_total = 0

    show_levels = False
    last_tablename = ""
    for line in database:
        tbloat = float(line["tbloat"])
        twasted = int(line["wastedbytes"])
        ibloat = float(line["ibloat"])
        iwasted = int(line["wastedibytes"])

        if line["schemaname"] + "." + line["tablename"] != last_tablename:
            table_abs_total += twasted
        index_abs_total += iwasted
        last_tablename = line["schemaname"] + "." + line["tablename"]

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
            if "%s_bloat_perc" % what in params:
                warn, crit = params["%s_bloat_perc" % what]
                if bloat >= crit:
                    yield 2, "{}.{} {} bloat: {}% (too high)".format(line["schemaname"], line["tablename"], what, bloat)
                    show_levels = True
                elif bloat >= warn:
                    yield 1, "{}.{} {} bloat: {}% (too high)".format(line["schemaname"], line["tablename"], what, bloat)
                    show_levels = True

            if "%s_bloat_abs" % what in params:
                warn, crit = params["%s_bloat_abs" % what]
                if wasted >= crit:
                    yield (
                        2,
                        "{}.{} wasted {} bytes: {} (too high)".format(
                            line["schemaname"],
                            line["tablename"],
                            what,
                            render.bytes(wasted),
                        ),
                    )
                    show_levels = True
                elif wasted >= warn:
                    yield (
                        1,
                        "{}.{} wasted {} bytes: {} (too high)".format(
                            line["schemaname"],
                            line["tablename"],
                            what,
                            render.bytes(wasted),
                        ),
                    )
                    show_levels = True

    if show_levels:
        levels_info = ["Levels:"]
        for what in ["table", "index"]:
            if "%s_bloat_perc" % what in params:
                levels_info.append(
                    "%s Perc (%.0f%%/%.0f%%)" % ((what.title(),) + params["%s_bloat_perc" % what])
                )
            if "%s_bloat_abs" % what in params:
                levels_info.append(
                    "%s Abs (%s/%s)"
                    % (
                        (what.title(),)
                        + tuple(render.bytes(int(x)) for x in params["%s_bloat_abs" % what])
                    )
                )
        yield 0, " ".join(levels_info)
    else:
        # No errors. Show some general information
        for what, perc_max, abs_max in [
            ("table", table_perc_max, table_abs_max),
            ("index", index_perc_max, index_abs_max),
        ]:
            yield (
                0,
                "Maximum {} bloat at {}.{}: {}".format(
                    what,
                    perc_max["schemaname"],
                    perc_max["tablename"],
                    render.percent(float(perc_max["%sbloat" % what[0]])),
                ),
            )
            yield (
                0,
                "Maximum wasted {}space at {}.{}: {}".format(
                    what,
                    abs_max["schemaname"],
                    abs_max["tablename"],
                    render.bytes(int(abs_max["wasted%sbytes" % (what == "index" and "i" or "")])),
                ),
            )

    # Summary information
    for what, total_value in [("table", table_abs_total), ("index", index_abs_total)]:
        yield (
            0,
            "Summary of top %d wasted %sspace: %s"
            % (len(database), what, render.bytes(total_value)),
            [("%sspace_wasted" % what, total_value)],
        )


check_info["postgres_bloat"] = LegacyCheckDefinition(
    name="postgres_bloat",
    parse_function=postgres.parse_dbs,
    service_name="PostgreSQL Bloat %s",
    discovery_function=discover_postgres_bloat,
    check_function=check_postgres_bloat,
    check_ruleset_name="db_bloat",
    check_default_parameters={
        "table_bloat_perc": (180.0, 200.0),  # WARN at 180%, CRIT at 200%
        "index_bloat_perc": (180.0, 200.0),
    },
)
