#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_license_state>>>
# Splunk_Enterprise_Splunk_Analytics_for_Hadoop_Download_Trial 5 30 524288000 1561977130 VALID
# Splunk_Forwarder 5 30 1048576 2147483647 VALID
# Splunk_Free 3 30 524288000 2147483647 VALID

# expiration_time default is warn/crit 14d/7d


# mypy: disable-error-code="var-annotated"

import collections
import time

from cmk.base.check_api import (
    get_age_human_readable,
    get_bytes_human_readable,
    get_timestamp_human_readable,
    LegacyCheckDefinition,
)
from cmk.base.config import check_info

SplunkLicenseState = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "SplunkLicenseState",
    [
        "max_violations",
        "window_period",
        "quota",
        "expiration_time",
        "time_to_expiration",
        "status",
    ],
)


def parse_splunk_license_state(string_table):
    parsed = {}

    for lcs_detail in string_table:
        try:
            label, max_violations, window_period, quota, expiration_time, status = lcs_detail

            time_to_expiration = float(expiration_time) - time.time()
            parsed.setdefault(label, []).append(
                SplunkLicenseState(
                    max_violations,
                    window_period,
                    get_bytes_human_readable(int(quota)),
                    get_timestamp_human_readable(int(expiration_time)),
                    time_to_expiration,
                    status,
                )
            )

        except (IndexError, ValueError):
            pass

    return parsed


def check_splunk_license_state(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    data = item_data[0]
    state = 0

    if data.status == "EXPIRED":
        state = params.get("state")

    yield state, "Status: %s" % data.status

    if data.time_to_expiration > 0:
        warn, crit = params["expiration_time"]
        state = 0

        infotext = "Expiration time: %s" % data.expiration_time

        if data.time_to_expiration <= crit:
            state = 2
        elif data.time_to_expiration <= warn:
            state = 1

        if state != 0:
            infotext += " (expires in {} - Warn/Crit at {}/{})".format(
                get_age_human_readable(data.time_to_expiration),
                get_age_human_readable(warn),
                get_age_human_readable(crit),
            )

        yield state, infotext

    yield 0, "Max violations: {} within window period of {} Days, Quota: {}".format(
        data.max_violations,
        data.window_period,
        data.quota,
    )


def discover_splunk_license_state(section):
    yield from ((item, {}) for item in section)


check_info["splunk_license_state"] = LegacyCheckDefinition(
    parse_function=parse_splunk_license_state,
    service_name="Splunk License %s",
    discovery_function=discover_splunk_license_state,
    check_function=check_splunk_license_state,
    check_ruleset_name="splunk_license_state",
    check_default_parameters={
        "state": 2,
        "expiration_time": (14 * 24 * 60 * 60, 7 * 24 * 60 * 60),
    },
)
