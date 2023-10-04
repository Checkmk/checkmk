#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from functools import cache
from pathlib import Path

from livestatus import SiteId

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

OMDConfig = dict[str, str]


@cache
def omd_site() -> SiteId:
    try:
        return SiteId(os.environ["OMD_SITE"])
    except KeyError:
        raise MKGeneralException(
            _("OMD_SITE environment variable not set. You can only execute this in an OMD site.")
        )


def url_prefix() -> str:
    return f"/{omd_site()}/"


def get_omd_config(omd_root: Path | None = None) -> OMDConfig:
    if omd_root is None:
        omd_root = cmk.utils.paths.omd_root

    site_conf = omd_root / "etc" / "omd" / "site.conf"

    omd_config: OMDConfig = {}
    with site_conf.open(encoding="utf-8") as f:
        for line in f:
            key, value = line.split("=")
            omd_config[key.strip()] = value.strip("'\n")
    return omd_config


def get_apache_port(omd_root: Path | None = None) -> int:
    port = get_omd_config(omd_root).get("CONFIG_APACHE_TCP_PORT")
    return 80 if port is None else int(port)
