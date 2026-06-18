#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from omdlib.config_api import Config


def _ln_sf(target: str, linkpath: Path) -> None:
    linkpath.unlink(missing_ok=True)
    os.symlink(target, linkpath)


def write_core_conf(_site_name: str, site_home: Path, config: Config) -> None:
    core = config["CORE"]

    nagios_conf = site_home / "etc" / "apache" / "conf.d" / "nagios.conf"
    microcore_mk = site_home / "etc" / "check_mk" / "conf.d" / "microcore.mk"
    core_init = site_home / "etc" / "init.d" / "core"
    cmc_bin = site_home / "etc" / "init.d" / "cmc"
    nagios_bin = site_home / "etc" / "init.d" / "nagios"
    core_config = site_home / "var" / "check_mk" / "core" / "config"
    livestatus_log = site_home / "var" / "log" / "livestatus.log"
    nagios_log = site_home / "var" / "log" / "nagios.log"

    # cleanup the former selection
    if nagios_conf.is_symlink():
        nagios_conf.unlink(missing_ok=True)

    if core != "cmc":
        microcore_mk.unlink(missing_ok=True)
        # Re-add links to logs
        if not livestatus_log.is_symlink():
            _ln_sf("../nagios/livestatus.log", livestatus_log)
        if not nagios_log.is_symlink():
            _ln_sf("../nagios/nagios.log", nagios_log)

    core_init.unlink(missing_ok=True)

    # now setup the new selection. Create the symlink only if its target exists.
    if core == "nagios":
        if nagios_bin.exists():
            os.symlink("nagios", core_init)
    elif core == "cmc":
        if cmc_bin.exists():
            os.symlink("cmc", core_init)
        content = """\
# Created by OMD hook CORE. Change with 'omd config'.
monitoring_core = 'cmc'
"""
        with open(microcore_mk, "w") as f:
            f.write(content)
        # Make sure that object configuration for core is present. Remove the old one
        # in advance to prevent problems with old configs during update when new config
        # creation fails
        if core_config.is_file():
            core_config.unlink(missing_ok=True)
        # Remove non relevant links to logs
        if livestatus_log.is_symlink():
            livestatus_log.unlink(missing_ok=True)
        if nagios_log.is_symlink():
            nagios_log.unlink(missing_ok=True)
