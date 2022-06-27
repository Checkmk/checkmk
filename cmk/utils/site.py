#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from livestatus import SiteId

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

OMDConfig = Dict[str, str]


@lru_cache
def omd_site() -> SiteId:
    try:
        return SiteId(os.environ["OMD_SITE"])
    except KeyError:
        raise MKGeneralException(
            _("OMD_SITE environment variable not set. You can only execute this in an OMD site.")
        )


def url_prefix() -> str:
    return "/%s/" % omd_site()


def get_omd_config(omd_root: Optional[Path] = None) -> OMDConfig:
    if omd_root is None:
        omd_root = cmk.utils.paths.omd_root

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
