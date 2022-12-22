#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os.path
from pathlib import Path
from typing import Final

import cmk.utils.paths

from .type_defs import FetcherType, SourceInfo

__all__ = ["make_file_cache_path_template", "make_persisted_section_dir"]


def make_persisted_section_dir(source: SourceInfo) -> Path:
    var_dir: Final = Path(cmk.utils.paths.var_dir)
    return {
        FetcherType.PIGGYBACK: var_dir / "persisted_sections" / source.ident / str(source.hostname),
        FetcherType.SNMP: var_dir / "persisted_sections" / source.ident / str(source.hostname),
        FetcherType.IPMI: var_dir / "persisted_sections" / source.ident / str(source.hostname),
        FetcherType.PROGRAM: var_dir / "persisted" / str(source.hostname),
        FetcherType.SPECIAL_AGENT: var_dir
        / "persisted_sections"
        / source.ident
        / str(source.hostname),
        FetcherType.PUSH_AGENT: var_dir
        / "persisted_sections"
        / source.ident
        / str(source.hostname),
        FetcherType.TCP: var_dir / "persisted" / str(source.hostname),
    }[source.fetcher_type]


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
