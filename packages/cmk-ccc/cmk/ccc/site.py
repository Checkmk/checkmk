#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

import json
import os
from functools import cache
from pathlib import Path

from livestatus import SiteId

from cmk.ccc.i18n import _

OMDConfig = dict[str, str]


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


def resource_attributes_from_config(omd_root: Path) -> dict[str, str]:
    """Get site specific tracing resource attributes

    Users can extend the builtin tracing resource attributes. This is useful
    for example to add environment specific attributes to the tracing spans.
    """
    attributes_path = omd_root / "etc" / "omd" / "resource_attributes_from_config.json"
    try:
        return json.loads(attributes_path.read_text())
    except OSError:
        return {}
