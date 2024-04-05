#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.db2 import parse_db2_dbs
from cmk.base.config import check_info

import cmk.plugins.lib.db
from cmk.agent_based.v2 import IgnoreResultsError, render

# No used space check for Tablsspaces with CONTENTS in ('TEMPORARY','UNDO')
# It is impossible to check the used space in UNDO and TEMPORARY Tablespaces
# These Types of Tablespaces are ignored in this plugin.
# This restriction is only working with newer agents, because we need an
# additional parameter at end if each datafile

# <<<db2_tablespaces>>>
# [[[db2taddm:CMDBS1]]]
# SYSCATSPACE DMS NORMAL 786304 786432 704224 82080
# USERSPACE1 DMS NORMAL 16874496 16875520 7010176 9809920
# SYSTOOLSPACE DMS NORMAL 32640 32768 3600 29040
# LARGESPACE2 DMS NORMAL 80896 81920 3072 77824
# TEMPSPACE1 SMS NORMAL 32 32 32 959659392
# USERSPACE2 SMS NORMAL 1327488 1327488 1327488 119957424
# LARGETEMP2 SMS NORMAL 32 32 32 119957424
# USERSPACE3 SMS NORMAL 1626712 1626712 1626712 119957424
# MYTMPSPACE SMS NORMAL 64 64 64 959659392
# SYSTOOLSTMPSPACE SMS NORMAL 32 32 32 959659392

db_get_tablespace_levels_in_bytes = cmk.plugins.lib.db.get_tablespace_levels_in_bytes


def inventory_db2_tablespaces(parsed):
    for instance, values in parsed[1].items():
        for table in values[1:]:
            yield f"{instance}.{table[0]}", {}


def check_db2_tablespaces(item, params, parsed):
    try:
        instance, tbsname = item.split(".")
    except ValueError:
        yield 3, "Invalid check item given (must be <instance>.<tablespace>)"
        return

    db = parsed[1].get(instance)
    if not db:
        raise IgnoreResultsError("Login into database failed")

    db_tables = {x[0]: x[1:] for x in db[1:]}
    tablespace = db_tables.get(tbsname)
    if not tablespace:
        return

    headers = db[0]
    tablespace_dict = dict(zip(headers[1:], tablespace))

    tbsp_type = tablespace_dict["TBSP_TYPE"]
    tbsp_state = tablespace_dict["TBSP_STATE"]
    usable = float(tablespace_dict["TBSP_USABLE_SIZE_KB"]) * 1024
    total = float(tablespace_dict["TBSP_TOTAL_SIZE_KB"]) * 1024
    used = float(tablespace_dict["TBSP_USED_SIZE_KB"]) * 1024
    free = float(tablespace_dict["TBSP_FREE_SIZE_KB"]) * 1024

    if tbsp_type == "SMS":
        usable = free  # for SMS free size is the amount of disk space available to the db file

    warn, crit, levels_text, as_perc = db_get_tablespace_levels_in_bytes(usable, params)

    infotext = f"{get_bytes_human_readable(used)} of {get_bytes_human_readable(usable)} used"
    perfdata = [
        ("tablespace_size", usable, max(0, total - (warn or 0)), max(0, total - (crit or 0))),
        ("tablespace_used", used),
        ("tablespace_max_size", total),
    ]
    yield 0, infotext, perfdata

    perc_free = 100.0 - used / usable * 100.0
    abs_free = usable - used

    state = 0
    infotext = "%s free" % render.percent(perc_free)
    if crit is not None and abs_free <= crit:
        state = 2
    elif warn is not None and abs_free <= warn:
        state = 1
    if state:
        if as_perc:
            value_str = render.percent(perc_free)
        else:
            value_str = get_bytes_human_readable(abs_free)
        infotext = f"only {value_str} left {levels_text}"
    yield state, infotext

    yield tbsp_state.lower() != "normal" and 1 or 0, "State: %s" % tbsp_state
    yield 0, "Type: %s" % tbsp_type


check_info["db2_tablespaces"] = LegacyCheckDefinition(
    parse_function=parse_db2_dbs,
    service_name="DB2 Tablespace %s",
    discovery_function=inventory_db2_tablespaces,
    check_function=check_db2_tablespaces,
    check_ruleset_name="db2_tablespaces",
    check_default_parameters={
        "levels": (10.0, 5.0),
        "magic_normsize": 1000,
    },
)
