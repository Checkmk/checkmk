#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.config_api import Config, Hook, null_action

from cmk.ccc.version import Edition


def write_mkeventd_conf(_site_name: str, site_home: Path, config: Config) -> None:
    enabled = "True" if config["MKEVENTD"] == "on" else "False"
    content = f"""\
# Set by OMD hook MKEVENTD, do not change here!
mkeventd_enabled = {enabled}
"""
    with open(site_home / "etc" / "check_mk" / "multisite.d" / "mkeventd.mk", "w") as f:
        f.write(content)
    with open(site_home / "etc" / "check_mk" / "conf.d" / "mkeventd.mk", "w") as f:
        f.write(content)


MKEVENTD = Hook(
    name="MKEVENTD",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda edition: "off" if edition is Edition.CLOUD else "on",
    activation=write_mkeventd_conf,
)

MKEVENTD_SNMPTRAP = Hook(
    name="MKEVENTD_SNMPTRAP",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    depends=lambda c: c.get("MKEVENTD") == "on",
    activation=null_action,
)

MKEVENTD_SYSLOG = Hook(
    name="MKEVENTD_SYSLOG",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    depends=lambda c: c.get("MKEVENTD") == "on",
    activation=null_action,
)

MKEVENTD_SYSLOG_TCP = Hook(
    name="MKEVENTD_SYSLOG_TCP",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    depends=lambda c: c.get("MKEVENTD") == "on",
    activation=null_action,
)
