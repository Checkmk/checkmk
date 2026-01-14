#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

import re
from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.plugins.brocade.lib import DETECT_MLX

check_info = {}

# TODO refactoring: use parse-function

brocade_mlx_states = {
    0: (1, "Slot is empty"),
    2: (1, "Module is going down"),
    3: (2, "Rejected due to wrong configuration"),
    4: (2, "Hardware is bad"),
    8: (1, "Configured / Stacking"),
    9: (1, "In power-up cycle"),
    10: (0, "Running"),
    11: (0, "Blocked for full height card"),
}


def parse_brocade_mlx(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["brocade_mlx"] = LegacyCheckDefinition(
    name="brocade_mlx",
    parse_function=parse_brocade_mlx,
    detect=DETECT_MLX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.2.2.1.1",
            oids=["1", "2", "12", "24", "25"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.2.11.1.1",
            oids=[OIDEnd(), "5"],
        ),
    ],
)


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def brocade_mlx_get_state(state):
    return brocade_mlx_states.get(state, (3, "Unhandled state - %d" % state))


def brocade_mlx_combine_item(id_, descr):
    if descr == "":
        return id_
    descr = re.sub(" *Module", "", descr)
    return f"{id_} {descr}"


#   .--Overall Status------------------------------------------------------.
#   |     ___                      _ _   ____  _        _                  |
#   |    / _ \__   _____ _ __ __ _| | | / ___|| |_ __ _| |_ _   _ ___      |
#   |   | | | \ \ / / _ \ '__/ _` | | | \___ \| __/ _` | __| | | / __|     |
#   |   | |_| |\ V /  __/ | | (_| | | |  ___) | || (_| | |_| |_| \__ \     |
#   |    \___/  \_/ \___|_|  \__,_|_|_| |____/ \__\__,_|\__|\__,_|___/     |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_brocade_mlx_module(info):
    inventory = []
    for module_id, module_descr, module_state, _mem_total, _mem_avail in info[0]:
        # do not inventorize modules reported as empty
        if module_state != "0":
            inventory.append((brocade_mlx_combine_item(module_id, module_descr), None))
    return inventory


def check_brocade_mlx_module(item, _no_params, info):
    for module_id, module_descr, module_state, _mem_total, _mem_avail in info[0]:
        if brocade_mlx_combine_item(module_id, module_descr) == item:
            return brocade_mlx_get_state(int(module_state))
    return 3, "Module not found"


check_info["brocade_mlx.module_status"] = LegacyCheckDefinition(
    name="brocade_mlx_module_status",
    service_name="Status Module %s",
    sections=["brocade_mlx"],
    discovery_function=discover_brocade_mlx_module,
    check_function=check_brocade_mlx_module,
)

# .
#   .--Memory--------------------------------------------------------------.
#   |               __  __                                                 |
#   |              |  \/  | ___ _ __ ___   ___  _ __ _   _                 |
#   |              | |\/| |/ _ \ '_ ` _ \ / _ \| '__| | | |                |
#   |              | |  | |  __/ | | | | | (_) | |  | |_| |                |
#   |              |_|  |_|\___|_| |_| |_|\___/|_|   \__, |                |
#   |                                                |___/                 |
#   +----------------------------------------------------------------------+


def parse_brocade_mlx_module_mem(info):
    parsed = {}
    for module_id, module_descr, module_state, mem_total, mem_avail in info[0]:
        item = brocade_mlx_combine_item(module_id, module_descr)
        try:
            _, state_readable = brocade_mlx_get_state(int(module_state))
        except ValueError:
            state_readable = "Device did not return any state"

        parsed.setdefault(
            item,
            {
                "state_readable": state_readable,
                "descr": module_descr,
            },
        )

        try:
            parsed[item]["mem_total"] = int(mem_total)
        except ValueError:
            pass

        try:
            parsed[item]["mem_avail"] = int(mem_avail)
        except ValueError:
            pass

    return parsed


def discover_brocade_mlx_module_mem(info):
    parsed = parse_brocade_mlx_module_mem(info)
    for k, v in parsed.items():
        # do not inventorize modules reported as empty or "Blocked for full height card"
        # and: monitor cpu only on NI-MLX and BR-MLX modules
        descr = v["descr"]
        if v["state_readable"] not in ["Slot is empty", "Blocked for full height card"] and (
            descr.startswith("NI-MLX") or descr.startswith("BR-MLX")
        ):
            yield k, {}


def check_brocade_mlx_module_mem(item, params, info):
    parsed = parse_brocade_mlx_module_mem(info)
    data = parsed.get(item)
    if data is None:
        return None

    state_readable = data["state_readable"]
    if state_readable.lower() != "running":
        return 3, "Module is not running (Current State: %s)" % state_readable

    levels = params.get("levels")
    try:
        return check_memory_element(
            "Usage",
            data["mem_total"] - data["mem_avail"],
            data["mem_total"],
            (
                (
                    "abs_used"
                    if isinstance(levels, tuple) and isinstance(levels[0], int)
                    else "perc_used"
                ),
                levels,
            ),
            metric_name="mem_used",
        )
    except KeyError:
        return None


check_info["brocade_mlx.module_mem"] = LegacyCheckDefinition(
    name="brocade_mlx_module_mem",
    service_name="Memory Module %s",
    sections=["brocade_mlx"],
    discovery_function=discover_brocade_mlx_module_mem,
    check_function=check_brocade_mlx_module_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={"levels": (80.0, 90.0)},
)

# .
#   .--CPU-----------------------------------------------------------------.
#   |                           ____ ____  _   _                           |
#   |                          / ___|  _ \| | | |                          |
#   |                         | |   | |_) | | | |                          |
#   |                         | |___|  __/| |_| |                          |
#   |                          \____|_|    \___/                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_brocade_mlx_module_cpu(info):
    for module_id, module_descr, module_state, _mem_total, _mem_avail in info[0]:
        # do not inventorize modules reported as empty or "Blocked for full height card"
        # and: monitor cpu only on NI-MLX and BR-MLX modules
        if module_state not in {"0", "11"} and (
            module_descr.startswith("NI-MLX") or module_descr.startswith("BR-MLX")
        ):
            yield brocade_mlx_combine_item(module_id, module_descr), {}


def check_brocade_mlx_module_cpu(item, params, info):
    warn, crit = params["levels"]
    for module_id, module_descr, module_state, _mem_total, _mem_avail in info[0]:
        if brocade_mlx_combine_item(module_id, module_descr) == item:
            if module_state != "10":
                return 3, "Module is not in state running"

            cpu_util1: str | int = ""
            cpu_util5: str | int = ""
            cpu_util60: str | int = ""
            cpu_util300: str | int = ""
            for oid_end, cpu_util in info[1]:
                if oid_end == "%s.1.1" % module_id:
                    cpu_util1 = saveint(cpu_util)
                if oid_end == "%s.1.5" % module_id:
                    cpu_util5 = saveint(cpu_util)
                if oid_end == "%s.1.60" % module_id:
                    cpu_util60 = saveint(cpu_util)
                if oid_end == "%s.1.300" % module_id:
                    cpu_util300 = saveint(cpu_util)

            if cpu_util1 == "" or cpu_util5 == "" or cpu_util60 == "" or cpu_util300 == "":
                return 3, "did not find all cpu utilization values in snmp output"

            perfdata = [
                ("cpu_util1", str(cpu_util1) + "%", "", "", 0, 100),
                ("cpu_util5", str(cpu_util5) + "%", "", "", 0, 100),
                ("cpu_util60", str(cpu_util60) + "%", warn, crit, 0, 100),
                ("cpu_util300", str(cpu_util300) + "%", "", "", 0, 100),
            ]

            status = 0
            errorstring = ""
            if cpu_util60 > warn:
                status = 1
                errorstring = "(!)"
            if cpu_util60 > crit:
                status = 2
                errorstring = "(!!)"

            return (
                status,
                f"CPU utilization was {cpu_util1}/{cpu_util5}/{cpu_util60}{errorstring}/{cpu_util300}% for the last 1/5/60/300 sec",
                perfdata,
            )

    return 3, "Module not found"


check_info["brocade_mlx.module_cpu"] = LegacyCheckDefinition(
    name="brocade_mlx_module_cpu",
    service_name="CPU utilization Module %s",
    sections=["brocade_mlx"],
    discovery_function=discover_brocade_mlx_module_cpu,
    check_function=check_brocade_mlx_module_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (80.0, 90.0)},
)
