#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

from livestatus import SiteId

from cmk.ccc.i18n import _

OMDConfig = dict[str, str]


@dataclass
class TraceSendConfig:
    enabled: bool
    target: Literal["local_site"] | str


#
# !!! This module seems completely useless !!!
#
# We should type `OMDConfig` correctly instead and pass this
# configuration block around instead.
#


@cache
def omd_site() -> SiteId:
    try:
        return SiteId(os.environ["OMD_SITE"])
    except KeyError as exc:
        raise RuntimeError(
            _("OMD_SITE environment variable not set. You can only execute this in an OMD site.")
        ) from exc


def url_prefix() -> str:
    return f"/{omd_site()}/"


def get_omd_config(omd_root: Path) -> OMDConfig:
    site_conf = omd_root / "etc" / "omd" / "site.conf"

    omd_config: OMDConfig = {}
    with site_conf.open(encoding="utf-8") as f:
        for line in f:
            key, value = line.split("=")
            omd_config[key.strip()] = value.strip("'\n")
    return omd_config


def get_apache_port(omd_root: Path) -> int:
    port = get_omd_config(omd_root).get("CONFIG_APACHE_TCP_PORT")
    return 80 if port is None else int(port)


def trace_receive_port(omd_root: Path) -> int:
    return int(get_omd_config(omd_root)["CONFIG_TRACE_RECEIVE_PORT"])


def trace_send_config(omd_root: Path) -> TraceSendConfig:
    config = get_omd_config(omd_root)
    return TraceSendConfig(
        enabled=config.get("CONFIG_TRACE_SEND") == "on",
        target=config.get("CONFIG_TRACE_SEND_TARGET", "local_site"),
    )
