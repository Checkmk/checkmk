#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# Valid
# <<<saprouter_cert>>>
# SSO for USER "prdadm"
#   with PSE file "/usr/users/prdadm/saprouter/local.pse"
#
# Validity  -  NotBefore:   Wed Mar 30 11:21:33 2016 (160330102133Z)
#               NotAfter:   Thu Mar 30 11:21:33 2017 (170330102133Z)

# No certificate
# <<<saprouter_cert>>>
# get_my_name: no PSE name supplied, no SSO credentials found!

# running seclogin with USER="root"
# seclogin: No SSO credentials available

# PSE broken
# <<<saprouter_cert>>>
# get_my_name: Couldn't open PSE "/usr/users/prdadm/saprouter/local.pse" (Decoding error)

# Suggested by customer


# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}


def parse_saprouter_cert(string_table):
    def parse_date(list_):
        time_struct = time.strptime(" ".join(list_), "%b %d %H:%M:%S %Y")
        return time.mktime(time_struct), "%s-%s-%s" % time_struct[:3]

    parsed = {}
    validity = None
    for line in string_table:
        if line[0] == "Validity":
            validity = "valid"
            parsed.setdefault(validity, {})

        if validity and "NotBefore:" in line:
            parsed[validity].setdefault("not_before", parse_date(line[-5:-1]))

        elif validity and ("NotAfter:" in line or "NotAfter" in line):
            parsed[validity].setdefault("not_after", parse_date(line[-5:-1]))

        elif " ".join(line[:3]).lower() == "sso for user":
            parsed.setdefault("sso_user", line[-1].replace('"', ""))

        elif " ".join(line[:3]).lower() == "with pse file":
            parsed.setdefault("pse_file", line[-1].replace('"', ""))

        elif not validity:
            parsed.setdefault("failed", [])
            parsed["failed"].append(" ".join(line))

    return parsed


def discover_saprouter_cert(parsed):
    if parsed:
        return [(None, None)]
    return []


def check_saprouter_cert(_no_item, params, parsed):
    if "valid" in parsed:
        _not_before, not_before_readable = parsed["valid"]["not_before"]
        not_after, not_after_readable = parsed["valid"]["not_after"]
        validity_age = not_after - time.time()

        warn, crit = params["validity_age"]
        infotext = f"Valid from {not_before_readable} to {not_after_readable}, {render.timespan(validity_age)} to go"

        state = 0
        if validity_age < crit:
            state = 2
        elif validity_age < warn:
            state = 1

        if state:
            infotext += f" (warn/crit below {render.timespan(warn)}/{render.timespan(crit)})"

        return state, infotext

    if "failed" in parsed:
        return 3, " - ".join(parsed["failed"])
    return None


check_info["saprouter_cert"] = LegacyCheckDefinition(
    name="saprouter_cert",
    parse_function=parse_saprouter_cert,
    service_name="SAP router certificate",
    discovery_function=discover_saprouter_cert,
    check_function=check_saprouter_cert,
    check_ruleset_name="saprouter_cert_age",
    check_default_parameters={
        "validity_age": (86400 * 30, 86400 * 7),
    },
)
