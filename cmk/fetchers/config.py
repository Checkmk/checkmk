#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import os.path
from pathlib import Path
from typing import assert_never

import cmk.utils.paths
from cmk.utils.hostaddress import HostName

from cmk.checkengine.fetcher import FetcherType

__all__ = ["make_file_cache_path_template", "make_persisted_section_dir"]


def make_persisted_section_dir(
    host_name: HostName, *, fetcher_type: FetcherType, ident: str, section_cache_path: Path
) -> Path:
    match fetcher_type:
        case FetcherType.NONE:
            return Path(os.devnull)
        case FetcherType.PIGGYBACK | FetcherType.SNMP | FetcherType.IPMI | FetcherType.PUSH_AGENT | FetcherType.SPECIAL_AGENT:
            return section_cache_path / "persisted_sections" / ident / str(host_name)
        case FetcherType.PROGRAM | FetcherType.TCP:
            return section_cache_path / "persisted" / str(host_name)
        case _:
            assert_never(fetcher_type)


def make_file_cache_path_template(
    *,
    fetcher_type: FetcherType,
) -> str:
    # We create a *template* and not a path, so string manipulation
    # is the right thing to do.
    match fetcher_type:
        case FetcherType.NONE:
            raise NotImplementedError()
        case FetcherType.PIGGYBACK:
            raise NotImplementedError()
        case FetcherType.SNMP:
            raise NotImplementedError()
        case FetcherType.IPMI:
            raise NotImplementedError()
        case FetcherType.SPECIAL_AGENT:
            raise NotImplementedError()
        case FetcherType.PROGRAM:
            return os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}")
        case FetcherType.PUSH_AGENT:
            raise NotImplementedError()
        case FetcherType.TCP:
            return os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}")
        case _:
            assert_never(fetcher_type)
