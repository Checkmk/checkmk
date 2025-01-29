#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, StringTable

check_info = {}


def check_wmic_process(item, params, info):
    name, memwarn, memcrit, pagewarn, pagecrit, cpuwarn, cpucrit = params
    count, mem, page, userc, kernelc = 0, 0, 0, 0, 0
    cpucores = 1
    if len(info) == 0:
        return (3, "No output from agent in section wmic_process")

    value_store = get_value_store()
    now = time.time()

    legend = info[0]
    for line in info[1:]:
        psinfo = dict(zip(legend, line))
        if psinfo.get("Name") is None:
            continue
        if "ThreadCount" in legend and psinfo["Name"].lower() == "system idle process":
            cpucores = int(psinfo["ThreadCount"])
        elif psinfo["Name"].lower() == name.lower():
            count += 1
            mem += int(psinfo["WorkingSetSize"])
            page += int(psinfo["PageFileUsage"])
            userc += int(psinfo["UserModeTime"])
            kernelc += int(psinfo["KernelModeTime"])

    mem_mb = mem / 1048576.0
    page_mb = page / 1048576.0
    user_per_sec = get_rate(
        value_store, "wmic_process.user.%s.%d" % (name, count), now, userc, raise_overflow=True
    )
    kernel_per_sec = get_rate(
        value_store, "wmic_process.kernel.%s.%d" % (name, count), now, kernelc, raise_overflow=True
    )
    user_perc = (user_per_sec / 100000.0) / cpucores
    kernel_perc = (kernel_per_sec / 100000.0) / cpucores
    cpu_perc = user_perc + kernel_perc
    perfdata = [
        ("mem", mem_mb, memwarn, memcrit),
        ("page", page_mb, pagewarn, pagecrit),
        ("user", user_perc, cpuwarn, cpucrit, 0, 100),
        ("kernel", kernel_perc, cpuwarn, cpucrit, 0, 100),
    ]

    messages = []
    messages.append("%d processes" % count)
    state = 0

    msg = f"{user_perc:.0f}%/{kernel_perc:.0f}% User/Kernel"
    if cpu_perc >= cpucrit:
        state = 2
        msg += "(!!) (critical at %d%%)" % cpucrit
    elif cpu_perc >= cpuwarn:
        state = 1
        msg += "(!) (warning at %d%%)" % cpuwarn
    messages.append(msg)

    msg = "%.1fMB RAM" % mem_mb
    if 0 < memcrit <= mem_mb:
        state = 2
        msg += "(!!) (critical at %d MB)" % memcrit
    elif 0 < memwarn <= mem_mb:
        state = max(1, state)
        msg += "(!) (warning at %d MB)" % memwarn
    messages.append(msg)

    msg = "%1.fMB Page" % page_mb
    if page_mb >= pagecrit:
        state = 2
        msg += "(!!) (critical at %d MB)" % pagecrit
    elif page_mb >= pagewarn:
        state = max(state, 1)
        msg += "(!) (warning at %d MB)" % pagewarn
    messages.append(msg)

    return (state, ", ".join(messages), perfdata)


def parse_wmic_process(string_table: StringTable) -> StringTable:
    return string_table


check_info["wmic_process"] = LegacyCheckDefinition(
    name="wmic_process",
    parse_function=parse_wmic_process,
    service_name="Process %s",
    check_function=check_wmic_process,
    check_ruleset_name="wmic_process",
)
