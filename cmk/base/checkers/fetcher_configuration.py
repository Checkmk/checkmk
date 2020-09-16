#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Dict, IO, List, Literal, Optional

from cmk.utils.type_defs import HostAddress, HostName

import cmk.base.config as config

from ._abstract import Mode
from ._checkers import make_sources

__all__ = ["dump", "dumps"]


def dump(hostname: HostName, ipaddress: Optional[HostAddress], file_: IO[str]) -> None:
    """Dump the configuration to `hostname` fetchers into `file_`."""
    file_.write(dumps(hostname, ipaddress))


def dumps(hostname: HostName, ipaddress: Optional[HostAddress]) -> str:
    """Return the configuration to `hostname` fetchers."""
    return json.dumps(_make(hostname, ipaddress))


def _make(
    hostname: HostName,
    ipaddress: Optional[HostAddress],
) -> Dict[Literal["fetchers"], List[Dict[str, Any]]]:
    return {
        "fetchers": [{
            "fetcher_type": c.fetcher_type.name,
            "fetcher_params": c.fetcher_configuration,
        } for c in make_sources(
            config.HostConfig.make_host_config(hostname),
            ipaddress,
            mode=Mode.NONE,
        )]
    }
