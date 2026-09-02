#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

import time
from collections.abc import Mapping, Sequence
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)


class Validity(TypedDict, total=False):
    not_before: tuple[float, str]
    not_after: tuple[float, str]


class Section(TypedDict, total=False):
    sso_user: str
    pse_file: str
    valid: Validity
    failed: list[str]


def parse_saprouter_cert(string_table: StringTable) -> Section:
    def parse_date(tokens: Sequence[str]) -> tuple[float, str]:
        time_struct = time.strptime(" ".join(tokens), "%b %d %H:%M:%S %Y")
        return time.mktime(time_struct), "%s-%s-%s" % time_struct[:3]

    section: Section = {}
    valid: Validity = {}
    failed: list[str] = []
    in_validity = False
    for line in string_table:
        if line[0] == "Validity":
            in_validity = True
            section.setdefault("valid", valid)

        if in_validity and "NotBefore:" in line:
            valid.setdefault("not_before", parse_date(line[-5:-1]))

        elif in_validity and ("NotAfter:" in line or "NotAfter" in line):
            valid.setdefault("not_after", parse_date(line[-5:-1]))

        elif " ".join(line[:3]).lower() == "sso for user":
            section.setdefault("sso_user", line[-1].replace('"', ""))

        elif " ".join(line[:3]).lower() == "with pse file":
            section.setdefault("pse_file", line[-1].replace('"', ""))

        elif not in_validity:
            section.setdefault("failed", failed)
            failed.append(" ".join(line))

    return section


agent_section_saprouter_cert = AgentSection(
    name="saprouter_cert",
    parse_function=parse_saprouter_cert,
)


def discover_saprouter_cert(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_saprouter_cert(
    params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    if "valid" in section:
        _not_before, not_before_readable = section["valid"]["not_before"]
        not_after, not_after_readable = section["valid"]["not_after"]
        validity_age = not_after - time.time()

        warn, crit = params["validity_age"]
        infotext = (
            f"Valid from {not_before_readable} to {not_after_readable}, "
            f"{render.timespan(validity_age)} to go"
        )

        state = State.OK
        if validity_age < crit:
            state = State.CRIT
        elif validity_age < warn:
            state = State.WARN

        if state is not State.OK:
            infotext += f" (warn/crit below {render.timespan(warn)}/{render.timespan(crit)})"

        yield Result(state=state, summary=infotext)
        return

    if "failed" in section:
        yield Result(state=State.UNKNOWN, summary=" - ".join(section["failed"]))


check_plugin_saprouter_cert = CheckPlugin(
    name="saprouter_cert",
    service_name="SAP router certificate",
    discovery_function=discover_saprouter_cert,
    check_function=check_saprouter_cert,
    check_ruleset_name="saprouter_cert_age",
    check_default_parameters={
        "validity_age": (86400 * 30, 86400 * 7),
    },
)
