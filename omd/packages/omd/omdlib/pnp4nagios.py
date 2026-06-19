#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from pathlib import Path

from omdlib.config_api import Config, Hook


def _set_gearman_perfdata(site_home: Path, value: str) -> None:
    perfdata = site_home / "etc" / "mod-gearman" / "perfdata.conf"
    if perfdata.is_file() and perfdata.stat().st_size > 0:
        content = perfdata.read_text()
        perfdata.write_text(
            re.sub(r"^perfdata=.*$", f"perfdata={value}", content, flags=re.MULTILINE)
        )


def write_pnp4nagios_conf(_site_name: str, site_home: Path, config: Config) -> None:
    nagios_d = site_home / "etc" / "nagios" / "nagios.d"
    pnp_cfg = nagios_d / "pnp4nagios.cfg"
    if config["PNP4NAGIOS"] == "on":
        if nagios_d.exists():
            pnp_cfg.unlink(missing_ok=True)
            os.symlink("../../pnp4nagios/nagios_npcdmod.cfg", pnp_cfg)
        _set_gearman_perfdata(site_home, "no")
        enabled = "True"
    elif config["PNP4NAGIOS"] == "gearman":
        if nagios_d.exists():
            pnp_cfg.unlink(missing_ok=True)
            os.symlink("../../pnp4nagios/nagios_gearman.cfg", pnp_cfg)
        _set_gearman_perfdata(site_home, "yes")
        enabled = "True"
    elif config["PNP4NAGIOS"] == "npcd":
        if nagios_d.exists():
            pnp_cfg.unlink(missing_ok=True)
            os.symlink("../../pnp4nagios/nagios_npcd.cfg", pnp_cfg)
        enabled = "True"
    else:
        pnp_cfg.unlink(missing_ok=True)
        _set_gearman_perfdata(site_home, "no")
        enabled = "False"

    (site_home / "etc" / "apache" / "conf.d" / "pnp4nagios.conf").unlink(missing_ok=True)
    with open(site_home / "etc" / "check_mk" / "conf.d" / "pnp4nagios.mk", "w") as f:
        f.write(
            f"""\
# Set by OMD hook PNP4NAGIOS, do not change here!
pnp4nagios_enabled = {enabled}
"""
        )


PNP4NAGIOS = Hook(
    name="PNP4NAGIOS",
    choices=[
        ("on", "enable bulk mode with npcdmod and npcd"),
        ("npcd", "enable bulk mode with npcd"),
        ("gearman", "enable gearman worker"),
        ("off", "disable"),
    ],
    default=lambda _edition: "on",
    depends=lambda c: c.get("CORE") not in ("cmc", "none"),
    activation=write_pnp4nagios_conf,
)
