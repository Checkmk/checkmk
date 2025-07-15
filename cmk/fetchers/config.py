#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import assert_never

from cmk.ccc.hostaddress import HostName

from cmk.checkengine.fetcher import FetcherType

__all__ = ["make_persisted_section_dir"]


def make_persisted_section_dir(
    host_name: HostName, *, fetcher_type: FetcherType, ident: str, section_cache_path: Path
) -> Path:
    match fetcher_type:
        case FetcherType.NONE:
            return Path(os.devnull)
        case (
            FetcherType.PIGGYBACK
            | FetcherType.SNMP
            | FetcherType.IPMI
            | FetcherType.PUSH_AGENT
            | FetcherType.SPECIAL_AGENT
        ):
            return section_cache_path / "persisted_sections" / ident / str(host_name)
        case FetcherType.PROGRAM | FetcherType.TCP:
            return section_cache_path / "persisted" / str(host_name)
        case _:
            assert_never(fetcher_type)
