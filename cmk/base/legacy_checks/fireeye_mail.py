#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_average, get_rate, get_value_store, SNMPTree, StringTable
from cmk.plugins.fireeye.lib import DETECT

check_info = {}


def fireeye_counter_generic(value, what, average):
    this_time = time.time()
    # 'what' is the readable description of the checked counter
    # (e.g. 'Infected URL')
    # For the counter variable name, we remove all spaces
    # (e.g. 'fireeye.infected.url')
    counter = "fireeye_mail.%s" % what.replace(" ", ".").lower()
    rate = get_rate(get_value_store(), counter, this_time, value, raise_overflow=True)
    state = 0
    if what == "Bypass" and rate > 0:
        state = 2
    # The perf-variable also uses the counter description as name
    # (e.g. 'infected_rate')
    perfdata = [("%s_rate" % what.split(" ")[0].lower(), rate)]
    if average:
        avg = get_average(get_value_store(), " %s avg" % counter, this_time, rate, average)
        return (state, "%s: %.2f mails/%d seconds" % (what, avg * average, average), perfdata)
    return (state, f"{what}: {rate:.2f} mails/s", perfdata)


#   .--mail----------------------------------------------------------------.
#   |                                                                      |
#   |                     __  __       _ _                                 |
#   |                    |  \/  |     (_) |                                |
#   |                    | \  / | __ _ _| |                                |
#   |                    | |\/| |/ _` | | |                                |
#   |                    | |  | | (_| | | |                                |
#   |                    |_|  |_|\__,_|_|_|                                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# .1.3.6.1.4.1.25597.13.1.1.0 2560224
# .1.3.6.1.4.1.25597.13.1.2.0 0
# .1.3.6.1.4.1.25597.13.1.3.0 2560224
# .1.3.6.1.4.1.25597.13.1.4.0 2864
# .1.3.6.1.4.1.25597.13.1.5.0 0
# .1.3.6.1.4.1.25597.13.1.6.0 2864
# .1.3.6.1.4.1.25597.13.1.7.0 2134871
# .1.3.6.1.4.1.25597.13.1.8.0 0
# .1.3.6.1.4.1.25597.13.1.9.0 2134871


def check_fireeye_mail(_no_item, params, info):
    mail_info = info[0][0:3]
    average = params.get("interval", 0)
    for index, mail_type in enumerate(["Total", "Infected", "Analyzed"]):
        yield fireeye_counter_generic(int(mail_info[index]), mail_type, average)


def parse_fireeye_mail(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_mail(info):
    yield from [(None, {})] if info else []


check_info["fireeye_mail"] = LegacyCheckDefinition(
    name="fireeye_mail",
    parse_function=parse_fireeye_mail,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=[
            "1",
            "4",
            "7",
            "10",
            "13",
            "16",
            "19",
            "22",
            "25",
            "28",
            "31",
            "34",
            "37",
            "50",
            "51",
            "52",
        ],
    ),
    service_name="Received Mail Rates",
    discovery_function=discover_fireeye_mail,
    check_function=check_fireeye_mail,
    check_ruleset_name="fireeye_mail",
)

#   .--attachment----------------------------------------------------------.
#   |                                                                      |
#   |               _   _             _                          _         |
#   |          /\  | | | |           | |                        | |        |
#   |         /  \ | |_| |_ __ _  ___| |__  _ __ ___   ___ _ __ | |_       |
#   |        / /\ \| __| __/ _` |/ __| '_ \| '_ ` _ \ / _ \ '_ \| __|      |
#   |       / ____ \ |_| || (_| | (__| | | | | | | | |  __/ | | | |_       |
#   |      /_/    \_\__|\__\__,_|\___|_| |_|_| |_| |_|\___|_| |_|\__|      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# .1.3.6.1.4.1.25597.13.1.19.0 3415541
# .1.3.6.1.4.1.25597.13.1.20.0 0
# .1.3.6.1.4.1.25597.13.1.21.0 3415541
# .1.3.6.1.4.1.25597.13.1.22.0 896
# .1.3.6.1.4.1.25597.13.1.23.0 0
# .1.3.6.1.4.1.25597.13.1.24.0 896
# .1.3.6.1.4.1.25597.13.1.25.0 1942580
# .1.3.6.1.4.1.25597.13.1.26.0 0
# .1.3.6.1.4.1.25597.13.1.27.0 1942580


def check_fireeye_attachment(_no_item, params, info):
    mail_info = info[0][6:9]
    average = params.get("interval", 0)
    for index, attachment_type in enumerate(
        ["Total Attachment", "Infected Attachment", "Analyzed Attachment"]
    ):
        yield fireeye_counter_generic(int(mail_info[index]), attachment_type, average)


def discover_fireeye_mail_attachment(info):
    yield from [(None, {})] if info else []


check_info["fireeye_mail.attachment"] = LegacyCheckDefinition(
    name="fireeye_mail_attachment",
    service_name="Mails Containing Attachment",
    sections=["fireeye_mail"],
    discovery_function=discover_fireeye_mail_attachment,
    check_function=check_fireeye_attachment,
    check_ruleset_name="fireeye_mail",
)

#   .--url-----------------------------------------------------------------.
#   |                                                                      |
#   |                _    _ _____  _                                       |
#   |               | |  | |  __ \| |                                      |
#   |               | |  | | |__) | |                                      |
#   |               | |  | |  _  /| |                                      |
#   |               | |__| | | \ \| |____                                  |
#   |                \____/|_|  \_\______|                                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .1.3.6.1.4.1.25597.13.1.10.0 34996161
# .1.3.6.1.4.1.25597.13.1.11.0 0
# .1.3.6.1.4.1.25597.13.1.12.0 34996161
# .1.3.6.1.4.1.25597.13.1.13.0 2011
# .1.3.6.1.4.1.25597.13.1.14.0 0
# .1.3.6.1.4.1.25597.13.1.15.0 2011
# .1.3.6.1.4.1.25597.13.1.16.0 5619681
# .1.3.6.1.4.1.25597.13.1.17.0 0
# .1.3.6.1.4.1.25597.13.1.18.0 5619681


def check_fireeye_url(_no_item, params, info):
    mail_info = info[0][3:6]
    average = params.get("interval", 0)
    for index, url_type in enumerate(["Total URL", "Infected URL", "Analyzed URL"]):
        yield fireeye_counter_generic(int(mail_info[index]), url_type, average)


def discover_fireeye_mail_url(info):
    yield from [(None, {})] if info else []


check_info["fireeye_mail.url"] = LegacyCheckDefinition(
    name="fireeye_mail_url",
    service_name="Mails Containing URL",
    sections=["fireeye_mail"],
    discovery_function=discover_fireeye_mail_url,
    check_function=check_fireeye_url,
    check_ruleset_name="fireeye_mail",
)

#   .--statistics----------------------------------------------------------.
#   |                                                                      |
#   |           _____ _        _   _     _   _                             |
#   |          / ____| |      | | (_)   | | (_)                            |
#   |         | (___ | |_ __ _| |_ _ ___| |_ _  ___ ___                    |
#   |          \___ \| __/ _` | __| / __| __| |/ __/ __|                   |
#   |          ____) | || (_| | |_| \__ \ |_| | (__\__ \                   |
#   |         |_____/ \__\__,_|\__|_|___/\__|_|\___|___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .1.3.6.1.4.1.25597.13.1.28.0 1133119
# .1.3.6.1.4.1.25597.13.1.29.0 0
# .1.3.6.1.4.1.25597.13.1.30.0 1133119
# .1.3.6.1.4.1.25597.13.1.31.0 1738052
# .1.3.6.1.4.1.25597.13.1.32.0 0
# .1.3.6.1.4.1.25597.13.1.33.0 1738053
# .1.3.6.1.4.1.25597.13.1.34.0 841
# .1.3.6.1.4.1.25597.13.1.35.0 0
# .1.3.6.1.4.1.25597.13.1.36.0 841
# .1.3.6.1.4.1.25597.13.1.37.0 2007
# .1.3.6.1.4.1.25597.13.1.38.0 0
# .1.3.6.1.4.1.25597.13.1.39.0 2007


def check_fireeye_mail_statistics(_no_item, params, info):
    statistics_info = info[0][9:13]
    average = params.get("interval", 0)
    value_store = get_value_store()
    for index, mail_containing in enumerate(
        [
            "Emails containing Attachment",
            "Emails containing URL",
            "Emails containing malicious Attachment",
            "Emails containing malicious URL",
        ]
    ):
        this_time = time.time()
        counter = "fireeye.stat.%s" % "".join(mail_containing.split(" ")[2:]).lower()
        rate = get_rate(
            get_value_store(), counter, this_time, int(statistics_info[index]), raise_overflow=True
        )
        perfdata = [(counter.replace(".", "_"), rate * 60)]
        if average:
            avg = get_average(value_store, f"{counter}.avg", this_time, rate, average)
            yield (
                0,
                "%s: %.2f per %d minutes"
                % (
                    mail_containing,
                    avg * 60 * average,
                    average,
                ),
                perfdata,
            )
        else:
            yield 0, f"{mail_containing}: {rate * 60:.2f} per minute", perfdata


def discover_fireeye_mail_statistics(info):
    yield from [(None, {})] if info else []


check_info["fireeye_mail.statistics"] = LegacyCheckDefinition(
    name="fireeye_mail_statistics",
    service_name="Mail Processing Statistics",
    sections=["fireeye_mail"],
    discovery_function=discover_fireeye_mail_statistics,
    check_function=check_fireeye_mail_statistics,
    check_ruleset_name="fireeye_mail",
)

#   .--received------------------------------------------------------------.
#   |                                                                      |
#   |         _____               _               _                        |
#   |        |  __ \             (_)             | |                       |
#   |        | |__) |___  ___ ___ ___   _____  __| |                       |
#   |        |  _  // _ \/ __/ _ \ \ \ / / _ \/ _` |                       |
#   |        | | \ \  __/ (_|  __/ |\ V /  __/ (_| |                       |
#   |        |_|  \_\___|\___\___|_| \_/ \___|\__,_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .1.3.6.1.4.1.25597.13.1.50.0 04/06/17 12:01:04
# .1.3.6.1.4.1.25597.13.1.51.0 04/06/17 12:16:03
# .1.3.6.1.4.1.25597.13.1.52.0 4282


def check_fireeye_mail_received(_no_item, params, info):
    start, end, received = info[0][13:16]
    yield 0, f"Mails received between {start} and {end}: {received}"
    start_timestamp = time.mktime(time.strptime(start, "%m/%d/%y %H:%M:%S"))
    end_timestamp = time.mktime(time.strptime(end, "%m/%d/%y %H:%M:%S"))
    rate = float(received) / (end_timestamp - start_timestamp)
    yield check_levels(
        rate,
        "mail_received_rate",
        params.get("rate"),
        human_readable_func=lambda x: f"{x:.2f}/s",
        infoname="Rate",
    )


def discover_fireeye_mail_received(info):
    yield from [(None, {})] if info else []


check_info["fireeye_mail.received"] = LegacyCheckDefinition(
    name="fireeye_mail_received",
    service_name="Mails Received",
    sections=["fireeye_mail"],
    discovery_function=discover_fireeye_mail_received,
    check_function=check_fireeye_mail_received,
    check_default_parameters={"rate": (6000, 7000)},
)
