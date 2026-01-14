#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, get_rate, get_value_store, OIDEnd, render, SNMPTree

check_info = {}

# Old comments:
# Strange: Channel IDs seem to be not unique. But the second
# usage has '0' in the docsIfUpChannelFrequency...

# Info might look different: on the one hand the channel id is the connector
# on the other hand the OID. In some cases the channel id is not unique:

# [[[u'4', u'3', u'38000000']], [[u'3', u'541092', u'36', u'6', u'498']], []]

# [[[u'1337', u'1', u'20000000'],
#  [u'1338', u'2', u'32000000'],
#  [u'1339', u'3', u'38000000'],
#  [u'1361', u'1', u'0'],
#  [u'1362', u'2', u'0'],
#  [u'1363', u'3', u'0'],
#  [u'1364', u'4', u'0']],
# [[u'1337', u'2262114535', u'322661943', u'406110', u'293'],
#  [u'1338', u'2567058620', u'5306417', u'78105', u'328'],
#  [u'1339', u'4222307191', u'4132447', u'19600', u'339'],
#  [u'1361', u'0', u'0', u'0', u'0'],
#  [u'1362', u'0', u'0', u'0', u'0'],
#  [u'1363', u'0', u'0', u'0', u'0'],
#  [u'1364', u'0', u'0', u'0', u'0']],
# [[u'1337', u'9', u'9', u'9', u'5'],
#  [u'1338', u'10', u'10', u'10', u'61'],
#  [u'1339', u'10', u'10', u'10', u'4'],
#  [u'1361', u'0', u'0', u'0', u'0'],
#  [u'1362', u'0', u'0', u'0', u'0'],
#  [u'1363', u'0', u'0', u'0', u'0'],
#  [u'1364', u'0', u'0', u'0', u'0']]]

# [[[u'4', u'3', u'32400000'],
#  [u'80', u'1', u'25200000'],
#  [u'81', u'2', u'27600000'],
#  [u'82', u'4', u'38800000']],
# [[u'3', u'104052489', u'22364', u'23308', u'389']],
# []]


def parse_docsis_channels_upstream(string_table):
    freq_info = string_table[0]
    freq_info_dict = {x[0]: x[1:] for x in freq_info}
    sig_info_dict = {x[0]: x[1:] for x in string_table[1]}
    cm_info_dict = {x[0]: x[1:] for x in string_table[2]}

    parsed = {}
    for endoid, (cid, freq_str) in freq_info_dict.items():
        unique_name = (
            cid if len(freq_info) == len({x[1] for x in freq_info}) else (f"{endoid}.{cid}")
        )

        data = []
        if endoid in sig_info_dict:
            data = sig_info_dict[endoid] + cm_info_dict.get(endoid, [])
        elif cid in sig_info_dict:
            data = sig_info_dict[cid] + cm_info_dict.get(cid, [])

        if data:
            parsed[unique_name] = [float(freq_str)] + data

    return parsed


def discover_docsis_channels_upstream(parsed):
    for unique_name, entry in parsed.items():
        if entry[0] != "0" and entry[4] != "0":
            yield unique_name, {}


def check_docsis_channels_upstream(item, params, parsed):
    if item in parsed:
        entry = parsed[item]
        mhz, unerroreds, correcteds, uncorrectables, signal_noise = entry[:5]

        # Signal Noise
        warn, crit = params["signal_noise"]

        yield check_levels(
            float(signal_noise) / 10,  # [dB]
            "signal_noise",
            (None, None, warn, crit),  # No upper levels, lower levels
            human_readable_func=lambda x: f"{x:.1f} dB",
            infoname="Signal/Noise ratio",
        )

        fields = [("frequency", float(mhz) / 1000000, "Frequency", "%.2f", " MHz")]
        if len(entry) >= 6:
            total, active, registered, avg_util = entry[5:9]
            fields += [
                ("total", int(total), "Modems total", "%d", ""),
                ("active", int(active), "Active", "%d", ""),
                ("registered", int(registered), "Registered", "%d", ""),
                ("util", int(avg_util), "Aaverage utilization", "%d", "%"),
            ]

        for varname, value, title, form, unit in fields:
            yield 0, title + ": " + (form + "%s") % (value, unit), [(varname, value)]

        # Handle codewords. These are counters.
        now = time.time()
        rates = {}
        total_rate = 0.0
        for what, counter in [
            (
                "unerrored",
                int(unerroreds),
            ),
            (
                "corrected",
                int(correcteds),
            ),
            ("uncorrectable", int(uncorrectables)),
        ]:
            rate = get_rate(get_value_store(), what, now, counter, raise_overflow=True)
            rates[what] = rate
            total_rate += rate

        if total_rate:
            for what, title in [
                (
                    "corrected",
                    "corrected errors",
                ),
                (
                    "uncorrectable",
                    "uncorrectable errors",
                ),
            ]:
                ratio = rates[what] / total_rate  # fixed: true-division
                perc = 100.0 * ratio
                warn, crit = params[what]
                infotext = f"{render.percent(perc)} {title}"

                if perc >= crit:
                    state = 2
                elif perc >= crit:
                    state = 1

                if state:
                    infotext += f" (warn/crit at {warn:.1f}/{crit:.1f}%)"

                yield state, infotext, [("codewords_" + what, ratio, warn / 100.0, crit / 100.0)]


check_info["docsis_channels_upstream"] = LegacyCheckDefinition(
    name="docsis_channels_upstream",
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4115.820.1.0.0.0.0.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4115.900.2.0.0.0.0.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.827"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20858.2.600"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.10.127.1.1.2.1",
            oids=[OIDEnd(), "1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.10.127.1.1.4.1",
            oids=[OIDEnd(), "2", "3", "4", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.116.1.4.1.1",
            oids=[OIDEnd(), "3", "4", "5", "7"],
        ),
    ],
    parse_function=parse_docsis_channels_upstream,
    service_name="Upstream Channel %s",
    discovery_function=discover_docsis_channels_upstream,
    check_function=check_docsis_channels_upstream,
    check_ruleset_name="docsis_channels_upstream",
    check_default_parameters={
        "signal_noise": (10.0, 5.0),  # dB
        "corrected": (5.0, 8.0),  # Percent
        "uncorrectable": (1.0, 2.0),  # Percent
    },
)
