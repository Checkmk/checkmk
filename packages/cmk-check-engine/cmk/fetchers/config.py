#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.hostaddress import HostName

__all__ = ["make_persisted_section_dir", "make_cached_snmp_sections_dir"]


def make_persisted_section_dir(
    host_name: HostName, *, ident: str, section_cache_path: Path
) -> Path:
    return section_cache_path / "persisted_sections" / ident / str(host_name)


def make_cached_snmp_sections_dir(section_cache_path: Path) -> Path:
    return section_cache_path / "snmp_cached_sections"  # TODO: move this to cmk.utils.paths
