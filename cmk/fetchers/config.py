#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import os.path
from pathlib import Path
from typing import assert_never, Final

import cmk.utils.paths
from cmk.utils.type_defs import HostName

from ._typedefs import FetcherType

__all__ = ["make_file_cache_path_template", "make_persisted_section_dir"]


def make_persisted_section_dir(
    host_name: HostName,
    *,
    fetcher_type: FetcherType,
    ident: str,
) -> Path:
    var_dir: Final = Path(cmk.utils.paths.var_dir)
    match fetcher_type:
        case FetcherType.NONE:
            return Path(os.devnull)
        case FetcherType.PIGGYBACK | FetcherType.SNMP | FetcherType.IPMI | FetcherType.PUSH_AGENT | FetcherType.SPECIAL_AGENT:
            return var_dir / "persisted_sections" / ident / str(host_name)
        case FetcherType.PROGRAM | FetcherType.TCP:
            return var_dir / "persisted" / str(host_name)
        case _:
            assert_never(fetcher_type)


def make_file_cache_path_template(
    *,
    fetcher_type: FetcherType,
    ident: str,
) -> str:
    # We create a *template* and not a path, so string manipulation
    # is the right thing to do.
    base_dir: Final = str(cmk.utils.paths.data_source_cache_dir)
    match fetcher_type:
        case FetcherType.NONE:
            return os.devnull
        case FetcherType.PIGGYBACK:
            return os.path.join(base_dir, ident, "{hostname}")
        case FetcherType.SNMP:
            return os.path.join(base_dir, ident, "{mode}", "{hostname}")
        case FetcherType.IPMI:
            return os.path.join(base_dir, ident, "{hostname}")
        case FetcherType.SPECIAL_AGENT:
            return os.path.join(base_dir, ident, "{hostname}")
        case FetcherType.PROGRAM:
            return os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}")
        case FetcherType.PUSH_AGENT:
            return os.path.join(base_dir, ident, "{hostname}", "agent_output")
        case FetcherType.TCP:
            return os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}")
        case _:
            assert_never(fetcher_type)
