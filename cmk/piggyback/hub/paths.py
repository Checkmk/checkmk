#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class PiggybackHubPaths:
    config: Path
    multisite_config: Path


def create_paths(root_path: Path) -> PiggybackHubPaths:
    return PiggybackHubPaths(
        config=root_path / "etc/check_mk/piggyback_hub.conf",
        multisite_config=root_path / "etc/check_mk/piggyback_hub.d/multisite.conf",
    )
