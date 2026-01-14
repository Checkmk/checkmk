#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output from agent
# <<<jar_signature>>>
# [[[bluecove-1.2.3-signed.jar]]]
# sm       308 Fri May 11 01:42:04 CEST 2007 javax/microedition/io/StreamConnectionNotifier.class
#
#       X.509, CN=MicroEmulator Team
#             [certificate expired on 2/10/12 6:19 PM]
#
#
#               s = signature was verified
#                 m = entry is listed in manifest
#                   k = at least one certificate was found in keystore
#                     i = at least one certificate was found in identity scope
#
#                     jar verified.
#
#                     Warning:
#                     This jar contains entries whose signer certificate has expired.


# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable

check_info = {}


def discover_jar_signature(info):
    inventory = []
    for line in info:
        if line[0].startswith("[[["):
            f = line[0][3:-3]
            inventory.append((f, {}))
    return inventory


def check_jar_signature(item, _no_params, info):
    in_block = False
    details = []
    in_cert = False
    cert = []
    for line in info:
        line = (" ".join(line)).strip()
        if line == "[[[%s]]]" % item:
            in_block = True
        elif in_block and line.startswith("[[["):
            break
        elif in_block and line.startswith("X.509"):
            in_cert = True
            cert = [line]
        elif (
            in_block
            and in_cert
            and line.startswith("[")
            and not line.startswith("[entry was signed on")
        ):
            in_cert = False
            cert.append(line)
            details.append(cert)

    if not details:
        return (2, "No certificate found")

    _cert_dn, cert_valid = details[0]

    # [certificate is valid from 3/26/12 11:26 AM to 3/26/17 11:36 AM]
    # [certificate will expire on 7/4/13 4:13 PM]
    # [certificate expired on 2/10/12 6:19 PM]
    if "will expire on " in cert_valid:
        expiry_date_text = cert_valid.split("will expire on ", 1)[1][:-1]
    elif "expired on" in cert_valid:
        expiry_date_text = cert_valid.split("expired on ", 1)[1][:-1]
    else:
        expiry_date_text = cert_valid.split("to ", 1)[1][:-1]
    expiry_date = time.mktime(time.strptime(expiry_date_text, "%m/%d/%y %I:%M %p"))
    expired_since = time.time() - expiry_date

    warn, crit = 60 * 86400, 30 * 86400

    state = 0
    if expired_since >= 0:
        status_text = (
            f"Certificate expired on {expiry_date_text} ({render.timespan(expired_since)} ago) "
        )
        state = 2

    else:
        status_text = (
            f"Certificate will expire on {expiry_date_text} (in {render.timespan(-expired_since)})"
        )
        if -expired_since <= crit:
            state = 2
        elif -expired_since <= warn:
            state = 1
        if state:
            status_text += f" (warn/crit below {render.timespan(warn)}/{render.timespan(crit)})"

    return state, status_text


def parse_jar_signature(string_table: StringTable) -> StringTable:
    return string_table


check_info["jar_signature"] = LegacyCheckDefinition(
    name="jar_signature",
    parse_function=parse_jar_signature,
    service_name="Jar-Signature %s",
    discovery_function=discover_jar_signature,
    check_function=check_jar_signature,
)
