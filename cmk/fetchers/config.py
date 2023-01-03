#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os.path
from pathlib import Path
from typing import Final

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
    return {
        FetcherType.PIGGYBACK: var_dir / "persisted_sections" / ident / str(host_name),
        FetcherType.SNMP: var_dir / "persisted_sections" / ident / str(host_name),
        FetcherType.IPMI: var_dir / "persisted_sections" / ident / str(host_name),
        FetcherType.PROGRAM: var_dir / "persisted" / str(host_name),
        FetcherType.SPECIAL_AGENT: var_dir / "persisted_sections" / ident / str(host_name),
        FetcherType.PUSH_AGENT: var_dir / "persisted_sections" / ident / str(host_name),
        FetcherType.TCP: var_dir / "persisted" / str(host_name),
    }[fetcher_type]


def make_file_cache_path_template(
    *,
    fetcher_type: FetcherType,
    ident: str,
) -> str:
    # We create a *template* and not a path, so string manipulation
    # is the right thing to do.
    base_dir: Final = str(cmk.utils.paths.data_source_cache_dir)
    return {
        FetcherType.PIGGYBACK: os.path.join(base_dir, ident, "{hostname}"),
        FetcherType.SNMP: os.path.join(base_dir, ident, "{mode}", "{hostname}"),
        FetcherType.IPMI: os.path.join(base_dir, ident, "{hostname}"),
        FetcherType.SPECIAL_AGENT: os.path.join(base_dir, ident, "{hostname}"),
        FetcherType.PROGRAM: os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}"),
        FetcherType.PUSH_AGENT: os.path.join(base_dir, ident, "{hostname}", "agent_output"),
        FetcherType.TCP: os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}"),
    }[fetcher_type]
