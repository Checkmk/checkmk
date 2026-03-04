#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from pathlib import Path
from typing import Self


@dataclasses.dataclass(frozen=True)
class SitePaths:
    home: str
    apache_conf: Path

    @classmethod
    def from_site_name(cls, site_name: str, omd_path: Path = Path("/omd/")) -> Self:
        return cls(
            home=str(omd_path / f"sites/{site_name}"),
            apache_conf=omd_path / f"apache/{site_name}.conf",
        )
