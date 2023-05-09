#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Dict, Optional

import cmk.utils.paths

OMDConfig = Dict[str, str]


def get_omd_config(omd_root: Optional[Path] = None) -> OMDConfig:
    if omd_root is None:
        omd_root = Path(cmk.utils.paths.omd_root)

    site_conf = omd_root / "etc" / "omd" / "site.conf"

    omd_config: OMDConfig = {}
    with site_conf.open(encoding="utf-8") as f:
        for line in f:
            key, value = line.split("=")
            omd_config[key.strip()] = value.strip("'\n")
    return omd_config


def get_apache_port(omd_root: Optional[Path] = None) -> int:
    port = get_omd_config(omd_root).get("CONFIG_APACHE_TCP_PORT")
    if port is None:
        return 80
    return int(port)
