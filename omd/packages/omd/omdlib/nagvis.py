#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from omdlib.config_api import Config, Hook


def write_nagvis_apache_conf(_site_name: str, site_home: Path, config: Config) -> None:
    nagvis_conf = site_home / "etc" / "apache" / "conf.d" / "nagvis.conf"
    nagvis_conf.unlink(missing_ok=True)
    if config["NAGVIS"] == "on":
        os.symlink("../../nagvis/apache.conf", nagvis_conf)


NAGVIS = Hook(
    name="NAGVIS",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    activation=write_nagvis_apache_conf,
)
